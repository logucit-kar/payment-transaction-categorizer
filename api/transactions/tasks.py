import requests
import os
from celery import shared_task
from .models import UploadBatch, UploadItem, Transaction
import time, math, os, json
from django.db import transaction as db_transaction

TAXONOMY_URL = os.getenv('TAXONOMY_HOST', 'http://taxonomy-service:8200')

TAXONOMY_BULK_URL = os.getenv('TAXONOMY_HOST_BULK', 'http://127.0.0.1:8200') + '/classify/bulk'  #The hostname only works inside Docker, so use the localhost address here for celery.
MAX_RETRIES = 5
BASE_DELAY = 2
BULK_CHUNK = 200   # number of items to send per classify/bulk call
DB_BULK_CHUNK = 500  # number of Transaction rows to bulk_create at once

def push_example(category, example_text):
    payload = {"category": category, "example": example_text}
    try:
        requests.post(f"{TAXONOMY_URL}/taxonomy/update", json=payload, timeout=5)
    except Exception as e:
        # in production you may want to queue retries
        pass

@shared_task(bind=True)
def process_upload_batch(self, batch_id):
    print("Processing batch:", batch_id)
    try:
        batch = UploadBatch.objects.get(id=batch_id)
    except UploadBatch.DoesNotExist:
        return {'error': 'batch not found'}

    batch.status = 'IN_PROGRESS'
    batch.save(update_fields=['status'])

    items_qs = batch.items.all()
    total = items_qs.count()
    batch.total_items = total
    batch.save(update_fields=['total_items'])

    saved_count = 0
    processed_count = 0

    # Collect payloads in lists (maintain mapping to UploadItem ids)
    id_to_item = {}
    payload_texts = []
    payload_items_order = []

    all_low_confidence = []

    for it in items_qs:
        payload = it.payload
        text = payload.get('description') or payload.get('desc') or ''
        payload_texts.append(text)
        payload_items_order.append(it)
        id_to_item[it.id] = it

    # Process in chunks (BULK_CHUNK) to send to taxonomy bulk classify
    created_transactions = []
    for i in range(0, len(payload_texts), BULK_CHUNK):
        chunk_texts = payload_texts[i:i+BULK_CHUNK]
        chunk_items = payload_items_order[i:i+BULK_CHUNK]

        # Retry with exponential backoff
        attempt = 0
        success = False
        resp_json = None
        while attempt < MAX_RETRIES and not success:
            try:
                r = requests.post(TAXONOMY_BULK_URL, json={'items': chunk_texts}, timeout=60)
                r.raise_for_status()
                resp_json = r.json()
                success = True
            except Exception as e:
                print("ERROR calling TAXONOMY SERVICE:", e)
                attempt += 1
                delay = BASE_DELAY * (2 ** (attempt - 1))
                time.sleep(delay)
        if not success:
            # mark these items as processed failed
            for it in chunk_items:
                it.processed = True
                it.saved = False
                it.error = f"taxonomy_bulk_failed after {MAX_RETRIES} attempts"
                it.save(update_fields=['processed', 'saved', 'error'])
                processed_count += 1
            batch.processed = processed_count
            batch.save(update_fields=['processed'])
            continue

        # resp_json expected { low_confidence: [ { text, category, score, entities }, ... ] }
        results = resp_json["high_confidence"] + resp_json["low_confidence"]

        # accumulate low-confidence items across all chunks to reprot later
        all_low_confidence.extend(resp_json["low_confidence"])
       
        print(len(results))
 
        for res_item, upload_item in zip(results, chunk_items):
            category = res_item.get('category', {}).get('name')
            score = res_item.get('score')
            entities = res_item.get('entities', [])

            payload = upload_item.payload
            tr = Transaction(
                description=payload.get('description') or payload.get('desc') or '',
                amount=payload.get('amount') or None,
                date=payload.get('date') or None,
                user_label=None,
                predicted_category=category,
                predicted_score=score,
                entities=entities
            )
            created_transactions.append((tr, upload_item))

            # mark upload_item processed but saved will be set after DB insertion
            upload_item.processed = True
            upload_item.error = ''
            upload_item.save(update_fields=['processed', 'error'])
            processed_count += 1

        # bulk insert DB_BULK_CHUNK at a time
        if len(created_transactions) >= DB_BULK_CHUNK:
            to_create = [t for (t, it) in created_transactions]
            with db_transaction.atomic():
                Transaction.objects.bulk_create(to_create)
            saved_count += len(to_create)
            # mark corresponding UploadItems saved=True
            for (_, it) in created_transactions:
                it.saved = True
                it.save(update_fields=['saved'])
            created_transactions = []
            batch.saved = saved_count
            batch.processed = processed_count
            batch.save(update_fields=['saved', 'processed'])

    # flush remaining
    if created_transactions:
        to_create = [t for (t, it) in created_transactions]
        with db_transaction.atomic():
            Transaction.objects.bulk_create(to_create)
        saved_count += len(to_create)
        for (_, it) in created_transactions:
            it.saved = True
            it.save(update_fields=['saved'])
        batch.saved = saved_count

    batch.processed = processed_count
    batch.status = 'COMPLETED'
    batch.low_confidence = all_low_confidence

    batch.save(update_fields=['processed','saved','status','low_confidence'])

    results_low_confidence = all_low_confidence
    # SAVE INTO DB so SSE can read it
   # batch.low_confidence = results_low_confidence
    #batch.save(update_fields=['low_confidence'])

    return {'saved': saved_count, 'processed': processed_count, 'results_low_confidence': results_low_confidence }