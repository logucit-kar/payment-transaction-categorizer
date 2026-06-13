# Payment Transaction Categorizer

Full-stack app for categorizing payment transactions with ML suggestions and human-in-the-loop corrections.

## Project structure

```
payment-transaction-categorizer/
├── backend/                 # Django + Django REST Framework
│   ├── manage.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── config/              # Project settings, URLs, WSGI, Celery
│   └── apps/
│       └── transactions/    # DRF API, models, Celery tasks
├── frontend/                # React + Vite SPA
│   └── src/
│       ├── App.jsx
│       ├── api/             # API client
│       └── components/
├── services/
│   └── taxonomy/            # FastAPI ML service (spaCy + sentence-transformers)
├── data/                    # Sample CSV/JSON datasets
├── docker-compose.yml
└── .env.example
```

## Architecture

1. **Frontend** (React) calls Django REST API and optionally the taxonomy service for live suggestions.
2. **Django** persists transactions in **PostgreSQL** and queues bulk uploads via **Celery** + **Redis**.
3. **Taxonomy service** returns category predictions; low-confidence rows are reviewed in the UI and fed back for learning.

## API (Django) — `http://localhost:8300`

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/api/transactions/` | List / create transactions |
| GET/POST | `/api/category-data/` | Category training examples |
| GET | `/api/batches/` | Upload batch history |
| POST | `/api/upload/` | Upload CSV or JSON batch |
| GET | `/api/upload/stream/<id>/` | SSE batch progress |
| POST | `/api/low-confidence/submit/` | Submit manual corrections |
| GET | `/api/transactions/export/csv/` | Export CSV |
| GET | `/api/transactions/export/json/` | Export JSON |

## API (Taxonomy) — `http://localhost:8200`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/taxonomy` | Current taxonomy |
| POST | `/taxonomy/update` | Add category examples |
| POST | `/match` | Single-text classification |
| POST | `/classify/bulk` | Bulk classification |

Interactive docs: `http://localhost:8200/docs`

## Local development

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis

### Setup

```bash
cp .env.example .env
# Edit .env if needed

python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
pip install -r services/taxonomy/requirements.txt
```

### Database

```bash
cd backend
python manage.py migrate
```

### Run services (separate terminals)

**Taxonomy service**

```bash
cd services/taxonomy
uvicorn main:app --host 0.0.0.0 --port 8200 --reload
```

**Django API**

```bash
cd backend
python manage.py runserver 8300
```

**Celery worker**

```bash
cd backend
celery -A config worker -l info
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Frontend environment

Create `frontend/.env` (optional):

```bash
VITE_API_URL=http://localhost:8300
VITE_TAXONOMY_URL=http://localhost:8200
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Django API | http://localhost:8300 |
| Taxonomy API | http://localhost:8200/docs |
| PostgreSQL | localhost:5432 |

## Data models

- **Transaction** — description, amount, date, predicted category/score, user label, NER entities
- **CategoryData** — labeled examples for taxonomy learning
- **UploadBatch** / **UploadItem** — bulk import progress and per-row state
