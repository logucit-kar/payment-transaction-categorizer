# Transaction Categorizer (Django + React + Taxonomy FastAPI)

## Overview
This repository contains:
- Django REST API (PostgreSQL) to store labeled transactions and examples
- Taxonomy FastAPI service with Named Entity extraction (spaCy) and semantic matching (sentence-transformers)
- React frontend (Vite) to enter transactions, view taxonomy suggestions, label transactions

## Quick start (development, Docker)
1. Copy `.env.example` to `.env` and adjust secrets if needed.
2. Build and run containers:
   ```bash
   docker compose up --build
3. Django API: http://localhost:8300

* DRF browsable API available

4. Taxonomy FastAPI docs: http://localhost:8200/docs

5. Frontend: http://localhost:5173

To run everything locally on a python virtual environment:
cd api/
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python3 manage.py makemigrations transactions
python3 manage.py migrate 
python3 manage.py runserver 8300

api/./venv/bin/python -m celery -A api worker -l info 

taxonomy-service/uvicorn app.main:app --host 0.0.0.0 --port 8200 —reload

frontend/npm install & npm run dev