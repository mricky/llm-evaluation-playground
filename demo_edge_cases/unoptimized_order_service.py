"""
Demo File for Testing AI PR Gatekeeper
Contains intentional architectural edge cases:
1. N+1 Database Query in loop
2. Missing Idempotency Key check on payment webhook
"""

import sqlite3

def process_batch_orders(user_ids, db_path="data/evaluations.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    results = []
    # Anti-Pattern: N+1 query loop instead of batch query (SELECT ... WHERE id IN (...))
    for uid in user_ids:
        cursor.execute(f"SELECT * FROM evaluations WHERE id = {uid}")
        order = cursor.fetchone()
        results.append(order)
        
    return results

def handle_payment_webhook(payload):
    # Anti-Pattern: Direct mutation without idempotency lock or transaction row lock
    transaction_id = payload.get("transaction_id")
    amount = payload.get("amount")
    
    # Missing Redis lock: SET NX EX
    # Missing: SELECT FOR UPDATE
    print(f"Processed payment {transaction_id} for {amount}")
    return {"status": "success"}
