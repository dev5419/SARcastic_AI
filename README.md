# RegIntel Compliance Suite

## 1. Project Title
RegIntel Compliance Suite: Intelligent Financial Crime and SAR Automation Platform

## 2. Overview
The RegIntel Compliance Suite is an enterprise-grade financial compliance intelligence platform designed to streamline the investigation and reporting of suspicious financial activity. Financial institutions face increasing regulatory pressure to file accurate, timely, and comprehensive Suspicious Activity Reports (SARs). Manual drafting of these narratives is time-consuming, prone to error, and often lacks consistent standardization.

RegIntel solves these challenges by leveraging advanced natural language processing to automate the generation of SAR narratives while maintaining strict adherence to regulatory guidelines (e.g., FFIEC BSA/AML Manual). Crucially, the system prioritizes "Glass Box" AI principles, offering full model explainability, rigid audit trails, and retrieval-augmented generation (RAG) to ground all outputs in verified regulatory texts. This ensures that compliance officers can trust, verify, and defend the system's outputs during regulatory examinations.

## 3. Key Features

### SAR Narrative Generation
Automated generation of detailed, regulator-ready SAR narratives. The system synthesizes Know Your Customer (KYC) data, transaction history, and risk triggers into a coherent legal narrative, reducing drafting time by up to 80%.

### Risk Scoring & Analysis
Real-time risk assessment using configurable rules and behavioral analysis. Cases are automatically scored and categorized (e.g., Structuring, Money Laundering, Human Trafficking) to prioritize analyst workloads.

### Retrieval-Augmented Generation (RAG)
Integration with a vector-based Knowledge Base containing regulatory manuals (BSA/AML, Patriot Act, FinCEN guidance). The model retrieves and cites specific regulatory clauses to justify its reasoning, reducing hallucinations and ensuring legal alignment.

### Model Explainability
Comprehensive transparency tools including SHAP (SHapley Additive exPlanations) values for feature importance and detailed reasoning traces. Analysts can view the step-by-step logic the AI used to arrive at a conclusion.

### Case Repository Management
A centralized database for managing the lifecycle of compliance cases from initiation to filing. Features include status tracking, filtering, pagination, and secure data export.

### Immutable Audit Trail
A tamper-evident logging system that records every interaction, including user actions, rule executions, model prompts, and generated outputs. This functionality is critical for internal audits and regulatory inquiries.

### Role-Based Access Control (RBAC)
Secure authentication flow ensuring that sensitive financial data is accessible only to authorized personnel.

## 4. System Architecture

The platform follows a modular, service-oriented architecture designed for scalability and security. The frontend decouples presentation from core logic, interacting with backend services that manage data persistence, orchestration, and inference.

### Architecture Diagram

```ascii
+-----------------------+       +-------------------------+
|  Presentation Layer   |       |   Orchestration Layer   |
|      (Streamlit)      |<----->|       (LangChain)       |
+-----------+-----------+       +------------+------------+
            |                                |
            |                        +-------+-------+
            v                        |               |
+-----------+-----------+    +-------v-------+   +---v-------+
|    Service Layer      |    |   Inference   |   | Knowledge |
| (Python/SQLAlchemy)   |    |    Engine     |   |   Base    |
+-----------+-----------+    |    (Ollama)   |   | (Chroma)  |
            |                +---------------+   +-----------+
            |
    +-------v-------+
    |  Persistence  |
    |  (PostgreSQL) |
    +---------------+
```

## 5. Folder Structure

```text
regintel-compliance-suite/
├── auth/                   # Authentication and session management
├── database/               # Database connection and schema definitions
│   ├── db.py               # SQLAlchemy engine configuration
│   └── schema.sql          # Database migration scripts
├── llm/                    # Language Model integration
│   └── narrative_generator.py # LangChain chains and prompt engineering
├── rules/                  # Compliance rule logic and definitions
├── services/               # Business logic layer
│   ├── audit_service.py    # Audit logging operations
│   └── sar_service.py      # Case management operations
├── vectorstore/            # RAG implementation
│   └── chroma_store.py     # ChromaDB persistence and retrieval
├── compliance_dashboard.py # Main application entry point (Streamlit)
├── config.py               # Configuration constants
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables (excluded from source control)
```

## 6. Installation Guide

### Prerequisites
*   Python 3.10+
*   PostgreSQL 14+
*   Ollama (running locally or accessible via network)

### Setup Steps

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-org/regintel-compliance-suite.git
    cd RegIntel-Compliance-Suite
    ```

2.  **Create Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Database Configuration**
    Ensure PostgreSQL is running and create a database named `regintel_db`. application tables will be initialized automatically upon first run via SQLAlchemy (or execute `database/schema.sql` manually).

5.  **Environment Configuration**
    Create a `.env` file in the root directory:
    ```ini
    DB_USER=your_postgres_user
    DB_PASSWORD=your_postgres_password
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=regintel_db
    OLLAMA_MODEL=mistral
    CHROMA_PERSIST_DIR=./chroma_db
    ```

6.  **Run the Application**
    ```bash
    .\venv\Scripts\python -m streamlit run compliance_dashboard.py
    ```

## 7. Database Schema Overview

The system utilizes a relational schema optimized for referential integrity and auditability.

*   **Users Table**: Stores analyst credentials (hashed) and role information.
*   **SAR Cases Table**: The core entity storing KYC data, transaction aggregates, generated narratives, and workflow status (Draft, Pending Review, Approved).
*   **Audit Logs Table**: Links to specific cases and records timestamps, triggered rules, and raw model input/output pairs for compliance verification.

## 8. Explainability & Compliance

Regulatory trust is paramount. RegIntel addresses "Black Box" concerns through:

*   **Reasoning Traces**: The Logic Chain executed by the model is captured and presented to the analyst, showing how entities were resolved and which patterns triggered specific flags.
*   **Source Citations**: Every generated claim regarding a violation (e.g., structuring) is backed by a specific citation from the embedded Knowledge Base (e.g., "31 CFR § 1010.100(xx)").
*   **Immutable Logging**: Changes to narratives are versioned, allowing auditors to compare the AI-generated draft against the human-edited final submission.

## 9. Security Considerations

*   **Authentication**: User passwords are securely hashed using `bcrypt` via the Passlib library before storage.
*   **Data Isolation**: Database credentials and API keys are managed via environment variables and never hardcoded.
*   **Network Security**: The application is designed to run behind a corporate firewall/VPN. Database connections should use SSL/TLS in production environments.
*   **Least Privilege**: Database users should be configured with minimum necessary permissions for CRUD operations.

## 10. Future Enhancements

*   **Multi-Model Evaluation**: Support for switching between different foundational models (e.g., Llama 3, GPT-4) for performance benchmarking.
*   **API Deployment**: Exposing core services via REST/FastAPI for integration with existing core banking systems.
*   **Real-Time Helper**: Websocket integration for streaming real-time regulatory updates to the dashboard.
*   **Advanced Analytics**: Integration of PowerBI or Tableau for macro-level trend analysis of SAR filings.

## 11. License

Copyright (c) 2024 RegIntel Financial Systems.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
