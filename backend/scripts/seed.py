import sys
import os
sys.path.append(os.getcwd())

from backend.database import engine
from sqlalchemy import text
from passlib.context import CryptContext
from datetime import datetime, timedelta
import random

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def seed():
    print("Starting database seeding...")
    with engine.begin() as conn:
        # 1. Reset Tables
        print("Resetting tables...")
        conn.execute(text("DROP TABLE IF EXISTS audit_logs CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS sar_cases CASCADE")) 
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        
        # 2. Create Schema
        print("Creating schema...")
        conn.execute(text("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL
            );

            CREATE TABLE sar_cases (
                id SERIAL PRIMARY KEY,
                analyst_id INT REFERENCES users(id),
                customer_name VARCHAR(255),
                kyc_data TEXT,
                transaction_data TEXT,
                generated_narrative TEXT,
                edited_narrative TEXT,
                status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE audit_logs (
                id SERIAL PRIMARY KEY,
                sar_id INT REFERENCES sar_cases(id),
                rules_triggered TEXT,
                llm_prompt TEXT,
                llm_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # 3. Seed Users (10)
        print("Seeding users...")
        users = [
            ("admin@regintel.com", "admin123", "Compliance Head"),
            ("sarah@regintel.com", "sarah123", "Analyst"),
            ("mike@regintel.com", "mike123", "Reviewer"),
            ("jane@regintel.com", "jane123", "MLRO"),
            ("david@regintel.com", "david123", "Analyst"),
            ("emma@regintel.com", "emma123", "Analyst"), 
            ("lucas@regintel.com", "lucas123", "Reviewer"),
            ("system@regintel.com", "system", "System"),
            ("testinfo@regintel.com", "test1234", "Analyst"),
            ("auditor@regintel.com", "audit123", "Auditor")
        ]
        
        user_ids = []
        for u, p, r in users:
            res = conn.execute(
                text("INSERT INTO users (username, password, role) VALUES (:u, :p, :r) RETURNING id"),
                {"u": u, "p": get_password_hash(p), "r": r}
            )
            user_ids.append(res.fetchone()[0])

        analysts = [uid for uid in user_ids if uid not in [1, 3, 4, 7, 10]] # Filtering roughly
        
        # 4. Seed Cases (50 Alerts -> 30 Cases)
        # We'll just create 30 cases directly, representing converted alerts.
        print("Seeding cases...")
        statuses = ["Open", "Review", "Pending Review", "Approved", "Filed", "Closed", "Draft"]
        
        for i in range(30):
            status = random.choice(statuses)
            # Override for specific counts requested
            if i < 5: status = "Draft"
            elif i < 7: status = "Filed"
            
            created_at = datetime.now() - timedelta(days=random.randint(0, 60))
            
            # Risk/Narrative Logic
            narrative = "Standard narrative generated for testing purposes."
            if i % 5 == 0: narrative += " Continuing activity detected."
            
            customer = f"Customer Entity {i+1}"
            kyc = f"{{'full_name': '{customer}', 'address': '123 Fake St'}}"
            tx = f"[{{'amount': {random.randint(5000, 50000)}, 'date': '2023-10-01'}}]"
            
            res = conn.execute(
                text("""
                    INSERT INTO sar_cases 
                    (analyst_id, customer_name, kyc_data, transaction_data, generated_narrative, status, created_at)
                    VALUES (:aid, :cust, :kyc, :tx, :nar, :stat, :cat)
                    RETURNING id
                """),
                {
                    "aid": random.choice(analysts) if analysts else 1,
                    "cust": customer,
                    "kyc": kyc,
                    "tx": tx,
                    "nar": narrative,
                    "stat": status,
                    "cat": created_at
                }
            )
            case_id = res.fetchone()[0]
            
            # 5. Seed Audit Logs
            conn.execute(
                text("""
                    INSERT INTO audit_logs (sar_id, rules_triggered, llm_prompt, llm_response, created_at)
                    VALUES (:cid, 'Rule-101: Formatting', 'Prompt used...', 'Response generated...', :cat)
                """),
                {"cid": case_id, "cat": created_at}
            )

    print("Seeding complete.")

if __name__ == "__main__":
    seed()
