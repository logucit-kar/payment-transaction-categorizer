from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import os, json
import torch
import spacy
from sentence_transformers import SentenceTransformer, util
from fastapi.middleware.cors import CORSMiddleware

APP_DIR = os.path.dirname(__file__)
TAX_PATH = os.path.join(APP_DIR, "taxonomy.json")

app = FastAPI(title="Taxonomy Service (Improved)")

LOW_SCORE_THRESHOLD = 0.6

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load spaCy
try:
    nlp = spacy.load("en_core_web_sm")
except:
    nlp = spacy.blank("en")

# Load sentence-transformer
MODEL_NAME = os.getenv("SENTE_MODEL", "all-mpnet-base-v2")
model = SentenceTransformer(MODEL_NAME)

# Load or create taxonomy
if os.path.exists(TAX_PATH):
    with open(TAX_PATH, "r", encoding="utf-8") as fh:
        taxonomy = json.load(fh)
else:
    taxonomy = [
        {"id": "1", "name": "Food & Drink", "examples": ["coffee", "restaurant", "cafe", "lunch"]},
        {"id": "2", "name": "Groceries", "examples": ["supermarket", "grocery", "daily essentials"]},
        {"id": "3", "name": "Transport", "examples": ["uber", "taxi", "bus", "fuel"]},
        {"id": "4", "name": "Utilities", "examples": ["internet", "electricity", "water"]},
        {"id": "5", "name": "Salary", "examples": ["salary", "payroll"]},
    ]
    with open(TAX_PATH, "w", encoding="utf-8") as fh:
        json.dump(taxonomy, fh, indent=2)


# ---------- Embedding Preparation (Centroid Method) ----------

def prepare_embeddings():
    cat_embeds = []
    cat_texts = []

    for c in taxonomy:
        # Expand text to improve similarity performance
        examples = c.get("examples", [])
        texts = [c["name"]] + examples

        # Encode list of example texts
        emb = model.encode(texts, convert_to_tensor=True)  # shape: n x 768

        # Mean pooling (centroid) gives stable category representation
        mean_emb = emb.mean(dim=0)

        cat_embeds.append(mean_emb)
        cat_texts.append(" | ".join(texts))

    return cat_texts, torch.stack(cat_embeds)


_cat_texts, _cat_embeds = prepare_embeddings()


# ---------- API Routes ----------

@app.get("/taxonomy")
def get_taxonomy():
    return taxonomy


@app.post("/taxonomy/update")
def update_taxonomy(payload: Dict[str, Any]):
    global taxonomy, _cat_texts, _cat_embeds

    if isinstance(payload, list):
        taxonomy = payload
    else:
        category = payload.get("category")
        example = payload.get("example")

        if not category or not example:
            raise HTTPException(status_code=400, detail="Invalid payload")

        found = next((c for c in taxonomy if c["name"].lower() == category.lower()), None)
        if found:
            found.setdefault("examples", []).append(example)
        else:
            taxonomy.append({
                "id": str(len(taxonomy) + 1),
                "name": category,
                "examples": [example]
            })

    with open(TAX_PATH, "w", encoding="utf-8") as fh:
        json.dump(taxonomy, fh, indent=2)

    _cat_texts, _cat_embeds = prepare_embeddings()
    return {"status": "ok", "count": len(taxonomy)}


@app.post("/match")
def match_text(payload: Dict[str, str]):
    text = payload.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")

    # NER
    doc = nlp(text)
    entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

    # Encode query
    qembed = model.encode(text, convert_to_tensor=True)

    # Cosine similarity
    sims = util.cos_sim(qembed, _cat_embeds)[0]
    best_idx = int(sims.argmax().cpu().numpy())
    raw_score = float(sims[best_idx])

    # Normalize score (-1 → 1) → (0 → 1)
    norm_score = (raw_score + 1) / 2

    return {
        "category": taxonomy[best_idx],
        "score": norm_score,
        "entities": entities
    }


# ---------- Bulk API ----------

class BulkClassifyRequest(BaseModel):
    items: List[str]

class BulkClassifyResponseItem(BaseModel):
    text: str
    category: Dict[str, Any]
    score: float
    entities: List[Dict[str, str]] = []

class FeedbackItem(BaseModel):
    text: str
    correct_category: str

class FeedbackRequest(BaseModel):
    feedback: List[FeedbackItem]



@app.post("/classify/bulk")
def classify_bulk(payload: BulkClassifyRequest):
    texts = payload.items
    if not texts:
        raise HTTPException(status_code=400, detail="Items required")

    qembeds = model.encode(texts, convert_to_tensor=True)
    sims = util.cos_sim(qembeds, _cat_embeds)

    high_confidence = []
    low_confidence = []

    for i, text in enumerate(texts):
        row = sims[i]
        best_idx = int(row.argmax().cpu().numpy())
        raw_score = float(row[best_idx])
        norm_score = (raw_score + 1) / 2

        doc = nlp(text)
        entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

        result = {
            "text": text,
            "category": taxonomy[best_idx],
            "score": norm_score,
            "entities": entities
        }
        
        if norm_score < LOW_SCORE_THRESHOLD:
            low_confidence.append(result)
        else:
            high_confidence.append(result)
            
    print(high_confidence)
    
    return {
        "high_confidence": high_confidence,
        "low_confidence": low_confidence   # UI uses this list for review
    }

@app.post("/feedback")
def receive_feedback(payload: FeedbackRequest):
    global taxonomy, _cat_texts, _cat_embeds

    from db import update_transaction_category  # you will create this

    for item in payload.feedback:
        text = item.text
        correct_cat = item.correct_category

        # Update PostgreSQL
        update_transaction_category(text, correct_cat)

        # Update taxonomy (learning)
        found = next((c for c in taxonomy if c["name"].lower() == correct_cat.lower()), None)
        if found:
            found.setdefault("examples", []).append(text)
        else:
            taxonomy.append({
                "id": str(len(taxonomy) + 1),
                "name": correct_cat,
                "examples": [text]
            })

    # Save taxonomy & rebuild embeddings
    with open(TAX_PATH, "w", encoding="utf-8") as fh:
        json.dump(taxonomy, fh, indent=2)

    _cat_texts, _cat_embeds = prepare_embeddings()

    return {"status": "updated", "updated_count": len(payload.feedback)}