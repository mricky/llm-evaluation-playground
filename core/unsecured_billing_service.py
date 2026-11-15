"""
UNSECURED BILLING SERVICE (INTENTIONAL ANTI-PATTERNS FOR AI GATEKEEPER TEST)
This file intentionally violates enterprise architectural and security standards:
1. SQL Injection vulnerability via raw f-string concatenation.
2. N+1 Query Anti-Pattern: Executing database queries inside a loop.
3. Missing Concurrency Control & Row Locking: Potential race condition on balance mutation.
4. Missing Idempotency Key validation on payment webhook ingress.
"""

import sqlite3
from typing import List, Dict, Any

class UnsecuredBillingService:
    def __init__(self, db_path: str = "data/evaluations.db"):
        self.db_path = db_path

    def get_account_by_number(self, account_number: str) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 🔴 CRITICAL VULNERABILITY: Raw SQL Injection vulnerability
        query = f"SELECT * FROM accounts WHERE account_number = '{account_number}'"
        cursor.execute(query)
        result = cursor.fetchone()
        conn.close()
        return {"account": result}

    def process_bulk_payouts(self, payouts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        results = []
        # 🔴 ARCHITECTURAL VIOLATION: N+1 Query loop (Query inside for loop without batching)
        for payout in payouts:
            user_id = payout["user_id"]
            amount = payout["amount"]
            
            # Fetch user without transaction lock (Missing SELECT FOR UPDATE)
            cursor.execute(f"SELECT balance FROM user_wallets WHERE user_id = {user_id}")
            row = cursor.fetchone()
            current_balance = row[0] if row else 0
            
            # Non-atomic balance update (Severe Race Condition)
            new_balance = current_balance - amount
            cursor.execute(f"UPDATE user_wallets SET balance = {new_balance} WHERE user_id = {user_id}")
            results.append({"user_id": user_id, "new_balance": new_balance})
            
        conn.commit()
        conn.close()
        return results

    def handle_payment_gateway_webhook(self, webhook_payload: Dict[str, Any]):
        # 🔴 ARCHITECTURAL VIOLATION: Missing Idempotency Key & Missing HMAC Signature Verification
        # Double-webhook delivery within 100ms will result in duplicate ledger credits!
        txn_id = webhook_payload.get("transaction_id")
        amount = webhook_payload.get("amount")
        user_id = webhook_payload.get("user_id")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE user_wallets SET balance = balance + {amount} WHERE user_id = {user_id}")
        conn.commit()
        conn.close()
        
        return {"status": "success", "transaction_id": txn_id}
