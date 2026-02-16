from sqlalchemy import text
from database.db import engine

def create_sar_case(analyst_id, data, generated_narrative):
    """
    Creates a new SAR case in database and returns the new ID.
    Always uses explicit transactions for safety.
    """
    with engine.begin() as connection:
        result = connection.execute(
            text("""
                INSERT INTO sar_cases
                (analyst_id, customer_name, kyc_data, transaction_data,
                 generated_narrative, status)
                VALUES
                (:analyst_id, :customer_name, :kyc, :transactions,
                 :narrative, 'Draft')
                RETURNING id
            """),
            {
                "analyst_id": analyst_id,
                "customer_name": data["kyc"]["full_name"],
                "kyc": str(data["kyc"]),
                "transactions": str(data["transactions"]),
                "narrative": generated_narrative
            }
        )
        return result.fetchone()[0]

def update_edited_narrative(sar_id, edited_text):
    """
    Updates SAR narrative after analyst edits.
    """
    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE sar_cases
                SET edited_narrative = :edited_text,
                    status = 'Pending Review'
                WHERE id = :sar_id
            """),
            {
                "edited_text": edited_text,
                "sar_id": sar_id
            }
        )

def approve_sar(sar_id):
    """
    Reviewer approves SAR.
    """
    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE sar_cases
                SET status = 'Approved'
                WHERE id = :sar_id
            """),
            {"sar_id": sar_id}
        )

def get_all_cases(limit=100):
    """
    Retrieves a list of SAR cases, ordered by creation date descending.
    """
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT id, customer_name, status, created_at, 
                       CASE 
                           WHEN status = 'Approved' THEN 'Low'
                           WHEN status = 'Pending Review' THEN 'Medium'
                           ELSE 'High'
                       END as risk_level
                FROM sar_cases
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"limit": limit}
        )
        return result.mappings().all()

def get_case_by_id(sar_id):
    """
    Retrieves full details of a specific SAR case.
    """
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT * FROM sar_cases WHERE id = :sar_id
            """),
            {"sar_id": sar_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None
