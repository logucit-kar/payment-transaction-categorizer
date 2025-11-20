from rest_framework import viewsets, status
from rest_framework.response import Response

from rest_framework.decorators import api_view
from .models import Transaction, CategoryData
from .serializers import TransactionSerializer, CategoryDataSerializer
from django.conf import settings
import requests
import os
from django.db import transaction

from django.http import StreamingHttpResponse
from .models import UploadBatch, UploadItem
from .tasks import process_upload_batch
from .serializers import UploadBatchSerializer
import json, csv
from io import StringIO

from django.http import HttpResponse, JsonResponse


TAXONOMY_URL = os.getenv('TAXONOMY_HOST', 'http://taxonomy-service:8200')

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all().order_by('-created_at')
    serializer_class = TransactionSerializer

    def create(self, request, *args, **kwargs):
        # create transaction, call taxonomy to get suggestion
        data = request.data.copy()
        print(data)
        description = data.get('description', '')
        try:
            r = requests.post(f"{TAXONOMY_URL}/match", json={"text": description}, timeout=5)
            if r.ok:
                js = r.json()
                data['predicted_category'] = js.get('category', {}).get('name')
                data['predicted_score'] = js.get('score')
                data['entities'] = js.get('entities') or []
        except Exception as e:
            # ignore taxonomy errors
            pass

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # If user_label provided in payload, save CategoryData and sync taxonomy
        if data.get('user_label'):
            # create example
            CategoryData.objects.create(category_name=data['user_label'], example_text=description)
            # push to taxonomy service
            try:
                requests.post(f"{TAXONOMY_URL}/taxonomy/update", json={"category": data['user_label'], "example": description}, timeout=5)
            except Exception:
                pass

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class CategoryDataViewSet(viewsets.ModelViewSet):
    queryset = CategoryData.objects.all().order_by('-created_at')
    serializer_class = CategoryDataSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # push update to taxonomy service
        try:
            requests.post(f"{TAXONOMY_URL}/taxonomy/update", json=serializer.data, timeout=5)
        except Exception:
            pass
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

# upload endpoint: accepts multipart file upload OR JSON body with items
@api_view(['POST'])
def upload_file(request):
    items = None
    filename = None

    if 'file' in request.FILES:
        f = request.FILES['file']
        filename = getattr(f, 'name', None)
        content = f.read().decode('utf-8')
        # CSV or JSON
        if filename and filename.lower().endswith('.csv'):
            sio = StringIO(content)
            reader = csv.DictReader(sio)
            items = [row for row in reader]
        else:
            try:
                items = json.loads(content)
            except Exception:
                return Response({'error': 'Invalid JSON file'}, status=400)
    else:
        items = request.data.get('items')
        if not items:
            return Response({'error': 'No items'}, status=400)

    # create batch
    batch = UploadBatch.objects.create(filename=filename, total_items=len(items), status='PENDING')

    # create UploadItem objects
    objs = [UploadItem(batch=batch, payload=item) for item in items]

    UploadItem.objects.bulk_create(objs)


    # kick off Celery task to process batch asynchronously and categorize the transactions
    resp = process_upload_batch.delay(batch.id)
    print("BATCHID->", batch.id)

    print("TESTING STREAMING RESPONSE")
    return Response({'batch_id': batch.id, 'message': 'Batch queued'})

# SSE stream generator
def event_stream(batch_id):
    import time
    from django.utils import timezone
    while True:
        try:
            batch = UploadBatch.objects.get(id=batch_id)
        except UploadBatch.DoesNotExist:
            yield f"data: {json.dumps({'error': 'not_found'})}\n\n"
            break
        payload = {
            'id': batch.id,
            'status': batch.status,
            'total_items': batch.total_items,
            'processed': batch.processed,
            'saved': batch.saved,
            'updated_at': batch.updated_at.isoformat(),
            'low_confidence': batch.low_confidence 
        }

        #if batch.status == "COMPLETED":
         #   payload['low_confidence'] = batch.low_confidence
        
        yield f"data: {json.dumps(payload)}\n\n"
        
        if batch.status in ('COMPLETED', 'FAILED'):
            break
        time.sleep(1)

# SSE view
def upload_stream(request, batch_id):
    response = StreamingHttpResponse(
        event_stream(batch_id),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

@api_view(['POST'])
def low_confidence_submit(request):
    items = request.data.get("items")

    if not items:
        return Response({"error": "No items provided"}, status=400)

    updated = 0

    with transaction.atomic():
        for it in items:
            text = it["text"]
            corrected = it["corrected"]

            if not corrected:
                continue

            # 1. Save corrected mapping for future training
            CategoryData.objects.create(
                category_name=corrected,
                example_text=text
            )

            # 2. Push to taxonomy-service for update
            try:
                requests.post(
                    f"{TAXONOMY_URL}/taxonomy/update",
                    json={"category": corrected, "example": text},
                    timeout=5
                )
            except Exception:
                pass

            # 3. Update existing Transaction row(s)
            Transaction.objects.filter(description=text).update(
                user_label=corrected
            )

            updated += 1

    return Response({"updated": updated}, status=200)

# UploadBatch history viewset
class UploadBatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UploadBatchSerializer

    def get_queryset(self):
        user = self.request.user
        return UploadBatch.objects.order_by('-created_at')

@api_view(['GET'])
def export_transactions_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(["id", "description", "amount", "date", "predicted_category", "predicted_score", "user_label", "entities"])

    for tx in Transaction.objects.all().order_by('-created_at'):
        writer.writerow([
            tx.id,
            tx.description,
            tx.amount,
            tx.date,
            tx.predicted_category,
            tx.predicted_score,
            tx.user_label,
            json.dumps(tx.entities)
        ])

    return response


@api_view(['GET'])
def export_transactions_json(request):
    data = list(Transaction.objects.all().order_by('-created_at').values())
    return JsonResponse(data, safe=False)