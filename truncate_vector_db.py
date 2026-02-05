"""
Quick command to truncate (delete all documents from) vector DB.
Usage: python truncate_vector_db.py
"""
from app.core.vector_db import VectorDBClient
import os

vdb = VectorDBClient(path=os.getenv("VECTOR_DB_PATH", "./vector_store"))

# Get all documents
all_docs = vdb.list_where(where={}, limit=5000)
print(f"Found {len(all_docs)} documents")

if len(all_docs) > 0:
    # Delete all by IDs
    all_ids = [doc['id'] for doc in all_docs]
    vdb.collection.delete(ids=all_ids)
    print(f"✓ Deleted {len(all_ids)} documents")
    
    # Clear hashstore
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "app", "hashstore.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM hashes")
        conn.commit()
        conn.close()
        print("✓ Cleared hashstore")
    
    # Verify
    remaining = vdb.list_where(where={}, limit=5000)
    print(f"Remaining: {len(remaining)}")
else:
    print("Vector DB is already empty")
