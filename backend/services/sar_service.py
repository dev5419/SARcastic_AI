from datetime import datetime
from sqlalchemy import text
from backend.database import engine
import pandas as pd
import io
import uuid
import json
from rules.suspicious_rules import evaluate_risk_model
from backend.services.audit_service import save_audit_log

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

def update_generated_narrative(sar_id, narrative_text):
    """
    Updates the generated_narrative field after LLM generation.
    Also moves status from Draft to Review.
    """
    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE sar_cases
                SET generated_narrative = :narrative,
                    status = 'Review'
                WHERE id = :sar_id
            """),
            {
                "narrative": narrative_text,
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
                SELECT id, customer_name, status, created_at, analyst_id, generated_narrative,
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

def get_dashboard_metrics():
    """
    Retrieves aggregate metrics for the dashboard from the database.
    """
    metrics = {
        "sar_filed_month": 0,
        "avg_time_to_file": 0,
        "sla_breach_pct": 0.0,
        "backlog_30_days": 0,
        "continuing_sar": 0
    }

    with engine.connect() as connection:
        # SAR Filed This Month
        res_filed = connection.execute(text("""
            SELECT COUNT(*) FROM sar_cases 
            WHERE created_at >= date_trunc('month', CURRENT_DATE)
        """)).scalar()
        metrics["sar_filed_month"] = res_filed or 0

        # Total open cases for SLA calculation
        total_open = connection.execute(text("""
            SELECT COUNT(*) FROM sar_cases
            WHERE status NOT IN ('Approved', 'Closed', 'Filed')
        """)).scalar() or 0

        # Backlog > 30 Days (Open cases created > 30 days ago)
        res_backlog = connection.execute(text("""
            SELECT COUNT(*) FROM sar_cases 
            WHERE created_at < CURRENT_DATE - INTERVAL '30 days'
            AND status NOT IN ('Approved', 'Closed', 'Filed')
        """)).scalar()
        metrics["backlog_30_days"] = res_backlog or 0

        # SLA Breach %
        if total_open > 0:
            metrics["sla_breach_pct"] = round((metrics["backlog_30_days"] / total_open) * 100, 1)

        # Avg Time to File (for closed/approved/filed cases)
        avg_days = connection.execute(text("""
            SELECT AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at)) / 86400)
            FROM sar_cases
            WHERE status IN ('Approved', 'Filed', 'Closed')
        """)).scalar()
        metrics["avg_time_to_file"] = round(float(avg_days), 1) if avg_days else 0

        # Continuing SAR Count
        res_continuing = connection.execute(text("""
            SELECT COUNT(*) FROM sar_cases 
            WHERE generated_narrative LIKE '%continuing activity%'
               OR generated_narrative LIKE '%recurring%'
        """)).scalar()
        metrics["continuing_sar"] = res_continuing or 0

    return metrics

def generate_regulatory_report():
    """
    Generates a regulatory text summary report of recent SAR activity.
    In a real system, this might generate a PDF or XML.
    """
    # 1. Fetch Key Stats
    metrics = get_dashboard_metrics()
    
    # 2. Construct Report
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = f"""
    FINANCIAL CRIMES ENFORCEMENT NETWORK (FinCEN) REPORT
    SAR ACTIVITY REVIEW - AUTOMATED GENERATION
    =========================================================
    GENERATED ON: {timestamp}
    REPORTING ENTITY: RegIntel Compliance Suite
    
    ---------------------------------------------------------
    EXECUTIVE SUMMARY
    ---------------------------------------------------------
    During the current reporting period, the system has tracked:
    - {metrics['sar_filed_month']} new SAR filings.
    - {metrics['continuing_sar']} cases of continuing suspicious activity.
    - {metrics['backlog_30_days']} cases exceeding standard review timelines.
    
    The average time to file is currently tracking at {metrics['avg_time_to_file']} days.
    
    ---------------------------------------------------------
    KEY RISK INDICATORS
    ---------------------------------------------------------
    High risk volume remains within operational tolerances, though SLA 
    breaches have been noted in {metrics['sla_breach_pct']}% of cases.
    
    Recommended Action: Review resource allocation for accelerated triage.
    
    [END OF REPORT]
    """
    return report

def process_csv_upload(file_content: bytes, filename: str, user_id: int):
    """
    Processes uploaded CSV file:
    1. Reads into DataFrame
    2. Validates Schema
    3. Runs Risk Engine
    4. Creates Case & Transactions in DB (Atomic Transaction)
    """
    try:
        df = pd.read_csv(io.BytesIO(file_content))
    except Exception as e:
        raise ValueError(f"Invalid CSV file: {str(e)}")

    # VALIDATION
    required_cols = {'customer_id', 'amount', 'transaction_date'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Missing required columns: {required_cols - set(df.columns)}")

    # CLEANUP / PREP
    # Ensure customer_id exists. If multiple, pick mode or first.
    customer_id = str(df['customer_id'].mode()[0]) if not df.empty else "Unknown"
    
    # RUN RISK ENGINE
    risk_result = evaluate_risk_model(df)
    
    # PREPARE DATA FOR DB
    tx_json = df.to_json(orient='records', date_format='iso')
    
    with engine.begin() as connection:
        # 1. Create SAR Case
        kyc_dummy = {
            "full_name": customer_id, 
            "customer_id": customer_id,
            "source": "CSV Upload",
            "filename": filename,
            "risk_score": risk_result['score'],
            "risk_level": risk_result['level'],
            "triggered_rules": risk_result['triggered_rules']
        }
        
        result = connection.execute(
            text("""
                INSERT INTO sar_cases
                (analyst_id, customer_name, kyc_data, transaction_data, generated_narrative, status)
                VALUES
                (:analyst_id, :customer_name, :kyc, :transactions, :narrative, 'Draft')
                RETURNING id
            """),
            {
                "analyst_id": user_id,
                "customer_name": customer_id,
                "kyc": json.dumps(kyc_dummy),
                "transactions": tx_json, # Compatibility with existing logic
                "narrative": "Pending Generation (Uploaded via CSV)"
            }
        )
        new_case_id = result.fetchone()[0]

        # 2. Insert Transactions into dedicated table
        tx_records = df.to_dict(orient='records')
        for record in tx_records:
            t_id = uuid.uuid4()
            
            # Map fields safely
            amt = record.get('amount', 0)
            t_date = record.get('transaction_date')
            cid = str(record.get('customer_id'))
            t_type = record.get('type', 'Standard')
            desc = record.get('description', '')
            merchant = record.get('merchant', '')
            country = record.get('country', 'US')

            connection.execute(
                text("""
                    INSERT INTO transactions 
                    (id, case_id, customer_id, amount, transaction_date, type, description, merchant, country)
                    VALUES (:id, :case_id, :cid, :amt, :t_date, :type, :desc, :merchant, :country)
                """),
                {
                    "id": t_id,
                    "case_id": new_case_id,
                    "cid": cid,
                    "amt": amt,
                    "t_date": t_date,
                    "type": t_type,
                    "desc": desc,
                    "merchant": merchant,
                    "country": country
                }
            )

    # 3. Create Audit Log (Moved outside transaction to ensure case is committed first)
    save_audit_log(
        new_case_id,
        json.dumps(risk_result['triggered_rules']),
        "CSV Upload & Risk Scoring",
        f"Uploaded {len(df)} transactions. Risk Score: {risk_result['score']}"
    )

    return {
        "case_id": new_case_id,
        "risk_score": risk_result['score'],
        "risk_level": risk_result['level'],
        "tx_count": len(df),
        "triggered_rules": risk_result['triggered_rules']
    }
