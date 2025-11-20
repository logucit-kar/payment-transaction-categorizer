import psycopg2
import os

DB_URL = os.getenv("POSTGRES_URL")

def update_transaction_category(text: str, category: str):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # You should index transactions by text or ID → adjust accordingly
    query = """
        UPDATE transactions
        SET category = %s
        WHERE id = %s;
    """

    cur.execute(query, (category, text))
    conn.commit()

    cur.close()
    conn.close()
