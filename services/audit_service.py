from sqlalchemy import text
from database.db import engine

def save_audit_log(sar_id, rules_triggered, llm_prompt, llm_response):
    """
    Saves audit information into audit_logs table
    """
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO audit_logs 
                (sar_id, rules_triggered, llm_prompt, llm_response)
                VALUES (:sar_id, :rules, :prompt, :response)
            """),
            {
                "sar_id": sar_id,
                "rules": str(rules_triggered),
                "prompt": llm_prompt,
                "response": llm_response
            }
        )

def get_audit_logs(limit=100):
    """
    Retrieves latest audit logs, joined with SAR case info if available.
    """
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT 
                    a.id, 
                    a.rules_triggered, 
                    a.created_at, 
                    a.llm_prompt, 
                    a.llm_response,
                    s.customer_name 
                FROM audit_logs a
                LEFT JOIN sar_cases s ON a.sar_id = s.id
                ORDER BY a.created_at DESC
                LIMIT :limit
            """),
            {"limit": limit}
        )
        return result.mappings().all()
