import streamlit as st
import pandas as pd
import altair as alt
import datetime
import json
import time
import os

# --- Backend Integrations ---
from services.sar_service import create_sar_case, get_all_cases, get_case_by_id
from services.audit_service import save_audit_log, get_audit_logs
from llm.narrative_generator import generate_sar_narrative
from vectorstore.chroma_store import seed_regulatory_knowledge_base, retrieve_relevant_docs

# Try importing passlib for secure hashing (as per requirements)
try:
    from passlib.hash import pbkdf2_sha256
except ImportError:
    pbkdf2_sha256 = None

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="RegIntel Compliance Suite",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

# Initialize Knowledge Base
if "kb_seeded" not in st.session_state:
    try:
        seed_regulatory_knowledge_base()
        st.session_state.kb_seeded = True
    except Exception as e:
        print(f"Vector Store Error: {e}")

# -----------------------------------------------------------------------------
# Database Connection Check
# -----------------------------------------------------------------------------
DB_CONNECTED = False
try:
    # simple check to see if we can query the DB
    # We catch broad exceptions in case the engine isn't even configured in .env
    cases = get_all_cases(limit=1)
    DB_CONNECTED = True
except Exception as e:
    # Fail silently to console, show toast to user
    print(f"DB Connection Warning: {e}")
    # We will trigger a toast later so it doesn't disappear instantly

# -----------------------------------------------------------------------------
# Authentication Logic
# -----------------------------------------------------------------------------
DEMO_USERS = {
    "admin@regintel.com": "admin123", # Password would be hashed in prod
    "sarah@regintel.com": "sarah123"
}

def verify_password(email, password):
    if email in DEMO_USERS and DEMO_USERS[email] == password:
        return True
    return False

# -----------------------------------------------------------------------------
# Login View
# -----------------------------------------------------------------------------
def render_login():
    st.markdown("""
    <style>
        .login-container { max-width: 400px; margin: 100px auto; padding: 40px; background-color: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #E0E0E0; }
        .login-header { text-align: center; margin-bottom: 30px; }
        .login-title { font-size: 1.8rem; font-weight: 700; color: #0A2540; font-family: 'Inter', sans-serif; }
        .login-sub { color: #5E6C84; font-size: 0.9rem; margin-top: 5px; font-family: 'Inter', sans-serif; }
        .stButton > button { width: 100%; background-color: #0A2540; color: white; border-radius: 4px; padding: 10px 0; font-weight: 600; }
        .stButton > button:hover { background-color: #0E355B; }
        div[data-testid="column"]:nth-of-type(2) { display: flex; flex-direction: column; justify-content: center; }
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown('<div class="login-header"><div class="login-title">RegIntel Suite</div><div class="login-sub">Secure Professional Access</div></div>', unsafe_allow_html=True)
        with st.form("login_form"):
            email = st.text_input("Email Address", placeholder="name@company.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            if st.form_submit_button("Sign In"):
                with st.spinner("Authenticating..."):
                    time.sleep(0.8)
                if verify_password(email, password):
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.success("Login successful")
                    st.rerun()
                else:
                    st.error("Invalid email or password")
        st.markdown('<div style="text-align: center; margin-top: 20px; font-size: 0.8rem; color: #999;">Forgot password? Contact IT Support.</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Design System
# -----------------------------------------------------------------------------
def load_design_system():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        :root { --primary-blue: #0A2540; --secondary-blue: #005F73; --bg-color: #F4F6F8; --card-bg: #FFFFFF; --text-primary: #172B4D; --text-secondary: #5E6C84; --border-color: #DFE1E6; --success: #36B37E; --danger: #FF5630; --warning: #FFAB00; }
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--text-primary); background-color: var(--bg-color); }
        section[data-testid="stSidebar"] { background-color: #FAFBFC; border-right: 1px solid var(--border-color); }
        .kpi-card { background-color: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); display: flex; flex-direction: column; height: 100%; }
        .kpi-title { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 8px; }
        .kpi-value { font-size: 1.8rem; font-weight: 700; color: var(--primary-blue); margin-bottom: 4px; }
        .content-card { background-color: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .card-header { font-size: 1.1rem; font-weight: 600; color: var(--primary-blue); margin-bottom: 15px; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
        .badge { padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; display: inline-block; }
        .badge-high { background-color: #FFEBE6; color: #BF2600; }
        .badge-medium { background-color: #FFFAE6; color: #FF8B00; }
        .badge-low { background-color: #E3FCEF; color: #006644; }
        .badge-closed { background-color: #E6E8EA; color: #42526E; }
        .badge-open { background-color: #DEEBFF; color: #0747A6; }
        .stButton button { background-color: var(--primary-blue); color: white; border: none; border-radius: 4px; font-weight: 500; }
        .stButton button:hover { background-color: #0E355B; }
        #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Components
# -----------------------------------------------------------------------------
def kpi_card(title, value, trend=None, trend_direction="up"):
    trend_html = ""
    if trend:
        color = "var(--success)" if trend_direction == "good" else ("var(--danger)" if trend_direction == "bad" else "var(--text-secondary)")
        arrow = "↑" if trend_direction == "bad" else "↓"
        if trend_direction == "good": arrow="↑" if "+" in trend else "↓"
        trend_html = f'<span style="color: {color}; font-size: 0.8rem; font-weight: 500;">{arrow} {trend} vs last month</span>'
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">{title}</div><div class="kpi-value">{value}</div>{trend_html}</div>', unsafe_allow_html=True)

def risk_chart(data=None):
    if data is None:
        # Fallback/Demo Data
        data = pd.DataFrame({
            'Risk Level': ['Low Risk', 'Medium Risk', 'High Risk', 'Critical'],
            'Cases': [450, 210, 85, 25]
        })
    
    base = alt.Chart(data).encode(
        theta=alt.Theta("Cases", stack=True),
        radius=alt.Radius("Cases", scale=alt.Scale(type="sqrt", zero=True, rangeMin=20)),
        color=alt.Color("Risk Level", scale=alt.Scale(
            domain=['Low Risk', 'Medium Risk', 'High Risk', 'Critical'],
            range=['#36B37E', '#FFAB00', '#FF5630', '#BF2600']
        )),
        tooltip=["Risk Level", "Cases"]
    )
    pie = base.mark_arc(outerRadius=100, innerRadius=60)
    text = base.mark_text(radius=120).encode(text="Cases", color=alt.value("#172B4D"))
    st.altair_chart((pie + text).properties(height=250), use_container_width=True)

# -----------------------------------------------------------------------------
# Views
# -----------------------------------------------------------------------------
def render_dashboard():
    st.title("Compliance Dashboard")
    
    # Check DB status
    if not DB_CONNECTED and "db_toast_shown" not in st.session_state:
        st.toast("⚠️ Database disconnected. Using Simulation Mode.", icon="⚠️")
        st.session_state.db_toast_shown = True

    # 1. Metrics
    total_cases = 1842 # Sim default
    if DB_CONNECTED:
        try:
            cases = get_all_cases(limit=1000)
            total_cases = len(cases)
        except: pass
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: kpi_card("Total Cases", f"{total_cases}", "+4.2%" if not DB_CONNECTED else None, "good")
    with col2: kpi_card("High Risk Cases", "126", "+12%", "bad")
    with col3: kpi_card("Pending Review", "48", "-5%", "good")
    with col4: kpi_card("Flagged Alerts", "315", "+2.5%", "bad")

    st.write("")
    
    # 2. Charts & Activity
    m_col1, m_col2 = st.columns([2, 1])
    with m_col1:
        st.markdown('<div class="content-card"><div class="card-header">Recent Activity</div>', unsafe_allow_html=True)
        if DB_CONNECTED:
            cases = get_all_cases(limit=5)
            df = pd.DataFrame(cases)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No cases found in database.")
        else:
            # Sim Table
            st.markdown("""
            <table class="custom-table" style="width:100%; font-size:0.9rem;">
                <thead style="background:#F4F5F7; color:#5E6C84;"><tr><th style="padding:10px;">ID</th><th>Analyst</th><th>Risk</th><th>Status</th></tr></thead>
                <tbody>
                    <tr style="border-bottom:1px solid #DFE1E6;"><td style="color:#0065FF; padding:10px;">CAS-2942</td><td>Sarah J.</td><td><span class="badge badge-high">High</span></td><td>Open</td></tr>
                    <tr style="border-bottom:1px solid #DFE1E6;"><td style="color:#0065FF; padding:10px;">CAS-2941</td><td>Mike R.</td><td><span class="badge badge-medium">Medium</span></td><td>Review</td></tr>
                    <tr><td style="color:#0065FF; padding:10px;">CAS-2940</td><td>David C.</td><td><span class="badge badge-low">Low</span></td><td>Closed</td></tr>
                </tbody>
            </table>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with m_col2:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Risk Distribution</div>', unsafe_allow_html=True)
        risk_chart() # Uses sim data for now as calculating risk distribution from DB requires aggregation query not yet in service
        st.markdown('</div>', unsafe_allow_html=True)

def render_case_creation():
    st.title("Create New SAR Case")
    
    with st.container():
        st.markdown('<div class="content-card"><div class="card-header">Case Information</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            customer_name = st.text_input("Customer Entity Name", value="John Doe")
            risk_category = st.selectbox("Risk Category", ["Structuring", "Money Laundering", "Human Trafficking"])
        with c2:
            account_numb = st.text_input("Account Number", value="ACC-998877")
            case_priority = st.selectbox("Priority", ["Standard", "Urgent", "Critical"])
            
        st.markdown("### Transaction Analysis")
        default_tx = "2023-10-20: Cash Deposit $9,500\n2023-10-21: Cash Deposit $9,000\n2023-10-22: Cash Deposit $9,800\nTotal triggers structuring threshold."
        tx_details = st.text_area("Transaction Details", height=150, value=default_tx)
        
        if st.button("Submit for Analysis", type="primary"):
            if not DB_CONNECTED:
                st.error("Cannot analyze: Database not connected. Please configure your .env file with DB credentials.")
            else:
                with st.spinner("🤖 AI Architecting SAR Narrative... (Consulting Vector DB)"):
                    data_payload = {
                        "kyc": {"full_name": customer_name, "date_of_birth": "1980-01-01", "address": "123 Main St"},
                        "accounts": [account_numb],
                        "activity_start": "2023-10-20",
                        "activity_end": "2023-10-22",
                        "total_amount": 28300.00,
                        "transactions": tx_details
                    }
                    rule_res = {"triggered_rules": f"Potential {risk_category} detected. Pattern: Multiple deposits < $10k."}

                    try:
                        prompt, narrative = generate_sar_narrative(data_payload, rule_res)
                        new_id = create_sar_case(1, data_payload, narrative)
                        save_audit_log(new_id, rule_res["triggered_rules"], prompt, narrative)
                        
                        st.success(f"Case {new_id} Created Successfully!")
                        
                        # Show Result
                        st.markdown("---")
                        st.subheader("Analysis Results")
                        st.markdown(f'<div style="background-color:#F8F9FA; border-left:4px solid #0A2540; padding:15px; border-radius:4px;">{narrative}</div>', unsafe_allow_html=True)
                        with st.expander("View Logic"):
                            st.text(f"Prompt Used:\n{prompt}")

                    except Exception as e:
                        st.error(f"Analysis Failed: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)

def render_case_repository():
    st.title("Case Repository")
    
    if not DB_CONNECTED:
        st.warning("Database unavailable. Showing simulation data.")
        # Sim Data
        sim_df = pd.DataFrame([
             {"Case ID": "CAS-1001", "Customer": "Acme Corp", "Status": "Open", "Risk": "High", "Date": "2023-10-25"},
             {"Case ID": "CAS-1002", "Customer": "John Doe", "Status": "Closed", "Risk": "Low", "Date": "2023-10-24"}
        ])
        st.markdown(f'<div class="content-card"><div class="card-header">Case List (Simulated)</div>', unsafe_allow_html=True)
        st.dataframe(sim_df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    cases = get_all_cases(limit=50)
    if not cases:
        st.info("No cases in repository. Create one in Case Management!")
        return
        
    df = pd.DataFrame(cases)
    st.markdown(f'<div class="content-card"><div class="card-header">Case List ({len(df)})</div>', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_audit_trail():
    st.title("Audit Trail")
    if not DB_CONNECTED:
        st.warning("Database unavailable.")
        return

    logs = get_audit_logs(limit=50)
    if not logs:
        st.info("No audit logs found.")
        return
        
    df = pd.DataFrame(logs)
    st.markdown('<div class="content-card"><div class="card-header">System Logs</div>', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_model_explainability():
    st.title("Model Explainability")
    st.info("This section queries the ChromaDB Vector Store for regulatory context.")
    
    query = st.text_input("Test RAG Query", "structuring threshold")
    if st.button("Retrieve Context"):
        docs = retrieve_relevant_docs(query)
        if docs:
            for d in docs:
                for item in d: # Chroma returns list of lists sometimes
                     st.markdown(f"> {item}")
        else:
             st.warning("No documents found.")

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    if not st.session_state.authenticated:
        render_login()
        return

    load_design_system()
    with st.sidebar:
        st.markdown('<div style="font-size: 1.2rem; font-weight: 700; color: #0A2540; margin-bottom: 20px;">RegIntel Suite</div>', unsafe_allow_html=True)
        st.caption(f"User: {st.session_state.user_email}")
        if st.button("Dashboard", use_container_width=True): st.session_state.page = "Dashboard"; st.rerun()
        if st.button("Case Management", use_container_width=True): st.session_state.page = "Case Creation"; st.rerun()
        if st.button("Case Repository", use_container_width=True): st.session_state.page = "Case Repository"; st.rerun()
        if st.button("Audit Trail", use_container_width=True): st.session_state.page = "Audit Trail"; st.rerun()
        if st.button("Explainability", use_container_width=True): st.session_state.page = "Model Explainability"; st.rerun()
        st.markdown("---")
        if st.button("Logout"): st.session_state.authenticated = False; st.rerun()

    if st.session_state.page == "Dashboard": render_dashboard()
    elif st.session_state.page == "Case Creation": render_case_creation()
    elif st.session_state.page == "Case Repository": render_case_repository()
    elif st.session_state.page == "Audit Trail": render_audit_trail()
    elif st.session_state.page == "Model Explainability": render_model_explainability()

if __name__ == "__main__":
    main()
