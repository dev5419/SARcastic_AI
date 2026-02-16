import streamlit as st
import pandas as pd
import altair as alt
import datetime
import json
import time
import os

# --- Backend Integrations ---
from services.sar_service import create_sar_case, get_all_cases, get_case_by_id, get_dashboard_metrics, generate_regulatory_report
from services.audit_service import save_audit_log, get_audit_logs, get_case_audit_history
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
    "admin@regintel.com": {"pass": "admin123", "role": "Compliance Head"},
    "sarah@regintel.com": {"pass": "sarah123", "role": "Analyst"},
    "mike@regintel.com": {"pass": "mike123", "role": "Senior Reviewer"},
    "jane@regintel.com": {"pass": "jane123", "role": "MLRO"}
}

def verify_password(email, password):
    if email in DEMO_USERS and DEMO_USERS[email]["pass"] == password:
        return DEMO_USERS[email]
    return None

# -----------------------------------------------------------------------------
# Views
# -----------------------------------------------------------------------------
def render_dashboard():
    # Header & Export Actions
    h_c1, h_c2 = st.columns([2, 1])
    with h_c1:
        st.title("Compliance Dashboard")
    with h_c2:
        st.markdown('<div style="display: flex; gap: 10px; justify-content: flex-end; align-items: center; height: 100%;">', unsafe_allow_html=True)
        # 1. Generate Regulatory Report (Backend)
        report_text = generate_regulatory_report()
        st.download_button(
            "📄 Gen. Report",
            data=report_text,
            file_name=f"SAR_Summary_{datetime.date.today()}.txt",
            mime="text/plain",
            help="Generate Regulatory SAR Summary Report (Text)"
        )
        
        # 2. Export Cases CSV (Frontend/Backend Logic)
        try:
             # CSV requires fetching all cases potentially
             all_cases = get_all_cases(limit=1000)
             csv_data = pd.DataFrame(all_cases).to_csv(index=False)
             st.download_button(
                 "📊 Export CSV",
                 data=csv_data,
                 file_name=f"cases_export_{datetime.date.today()}.csv",
                 mime="text/csv"
             )
        except:
             st.button("📊 Export CSV", disabled=True)

        # 3. Export PDF (Mock)
        if st.button("🖨️ PDF", help="Export Dashboard View as PDF"):
             st.toast("Processing PDF Export... (Sent to print queue)", icon="🖨️")

        st.markdown('</div>', unsafe_allow_html=True)
    
    # Check DB status
    if not DB_CONNECTED and "db_toast_shown" not in st.session_state:
        st.toast("🚨 Database connection failed. Some features may be limited.", icon="🚨")
        st.session_state.db_toast_shown = True

# -----------------------------------------------------------------------------
# Login View
# -----------------------------------------------------------------------------
def render_login():
    st.markdown("""
    <style>
        .login-container { max-width: 400px; margin: 100px auto; padding: 32px; background-color: #102A43; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); border: 1px solid #2A3F55; }
        .login-header { text-align: center; margin-bottom: 24px; }
        .login-title { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; font-family: 'Inter', sans-serif; }
        .login-sub { color: #B0B8C1; font-size: 0.9rem; margin-top: 5px; font-family: 'Inter', sans-serif; }
        .stButton > button { width: 100%; background-color: #C9A227; color: #0B1F3A; border-radius: 6px; padding: 8px 0; font-weight: 600; }
        .stButton > button:hover { background-color: #E3B42A; color: #000000; }
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
                user_info = verify_password(email, password)
                if user_info:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.user_role = user_info["role"]
                    st.success(f"Login successful. Welcome {user_info['role']}")
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
        :root { --primary-gold: #C9A227; --bg-color: #0B1F3A; --card-bg: #102A43; --text-primary: #FFFFFF; --text-secondary: #B0B8C1; --border-color: #2A3F55; --success: #0D9488; --danger: #B91C1C; --warning: #D97706; }
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--text-primary); background-color: var(--bg-color); }
        section[data-testid="stSidebar"] { background-color: #0E243D; border-right: 1px solid var(--border-color); }
        .kpi-card { background-color: var(--card-bg); border: 1px solid var(--border-color); border-radius: 6px; padding: 19px; box-shadow: 0 1px 3px rgba(0,0,0,0.3); display: flex; flex-direction: column; height: 100%; }
        .kpi-title { font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px; }
        .kpi-value { font-size: 1.8rem; font-weight: 700; color: var(--primary-gold); margin-bottom: 3px; }
        .content-card { background-color: var(--card-bg); border: 1px solid var(--border-color); border-radius: 6px; padding: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.3); margin-bottom: 16px; }
        .card-header { font-size: 1.1rem; font-weight: 600; color: var(--primary-gold); margin-bottom: 12px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px; }
        .badge { padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; display: inline-block; }
        .badge-high { background-color: rgba(185, 28, 28, 0.2); color: #B91C1C; border: 1px solid #B91C1C; }
        .badge-medium { background-color: rgba(217, 119, 6, 0.2); color: #D97706; border: 1px solid #D97706; }
        .badge-low { background-color: rgba(13, 148, 136, 0.2); color: #0D9488; border: 1px solid #0D9488; }
        .badge-closed { background-color: #2A3F55; color: #B0B8C1; }
        .badge-open { background-color: rgba(201, 162, 39, 0.2); color: #C9A227; }
        .stButton button { background-color: var(--primary-gold); color: #0B1F3A; border: none; border-radius: 6px; font-weight: 600; }
        .stButton button:hover { background-color: #E3B42A; color: #000000; }
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
            range=['#0D9488', '#D97706', '#B91C1C', '#8B0000']
        )),
        tooltip=["Risk Level", "Cases"]
    )
    pie = base.mark_arc(outerRadius=100, innerRadius=60)
    text = base.mark_text(radius=120).encode(text="Cases", color=alt.value("#FFFFFF"))
    st.altair_chart((pie + text).properties(height=250), use_container_width=True)

def case_aging_heatmap(cases_data=None):
    data = None
    
    if cases_data:
        # Process real data
        # Assume cases_data is a list of dicts with 'created_at' and 'risk_level'
        # We need to calculate age in days
        now = datetime.datetime.now()
        processed_rows = []
        
        for case in cases_data:
            created_at = case.get('created_at')
            risk = case.get('risk_level', 'Medium')
            
            if created_at:
                if isinstance(created_at, str):
                    # formatting might vary, but let's assume iso or simple date
                    try:
                        c_date = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S.%f")
                    except:
                        try:
                             c_date = datetime.datetime.strptime(created_at, "%Y-%m-%d")
                        except:
                             c_date = now # Fallback
                else:
                    c_date = created_at
                
                days_old = (now - c_date).days
                
                bucket = "60+ Days"
                if days_old <= 7: bucket = "0-7 Days"
                elif days_old <= 15: bucket = "8-15 Days"
                elif days_old <= 30: bucket = "16-30 Days"
                elif days_old <= 60: bucket = "31-60 Days"
                
                processed_rows.append({"Risk": risk, "Bucket": bucket})
        
        if processed_rows:
            df = pd.DataFrame(processed_rows)
            data = df.groupby(['Risk', 'Bucket']).size().reset_index(name='Count')

    if data is None or data.empty:
        # Fallback/Demo Data
        data = pd.DataFrame([
            {"Risk": "High", "Bucket": "0-7 Days", "Count": 5},
            {"Risk": "High", "Bucket": "8-15 Days", "Count": 12},
            {"Risk": "High", "Bucket": "16-30 Days", "Count": 8},
            {"Risk": "High", "Bucket": "31-60 Days", "Count": 4},
            {"Risk": "High", "Bucket": "60+ Days", "Count": 2},
            {"Risk": "Medium", "Bucket": "0-7 Days", "Count": 15},
            {"Risk": "Medium", "Bucket": "8-15 Days", "Count": 10},
            {"Risk": "Medium", "Bucket": "16-30 Days", "Count": 5},
            {"Risk": "Medium", "Bucket": "31-60 Days", "Count": 1},
            {"Risk": "Medium", "Bucket": "60+ Days", "Count": 0},
            {"Risk": "Low", "Bucket": "0-7 Days", "Count": 25},
            {"Risk": "Low", "Bucket": "8-15 Days", "Count": 15},
            {"Risk": "Low", "Bucket": "16-30 Days", "Count": 2},
            {"Risk": "Low", "Bucket": "31-60 Days", "Count": 0},
            {"Risk": "Low", "Bucket": "60+ Days", "Count": 0},
        ])

    # Ensure correct ordering of buckets and risk
    bucket_order = ["0-7 Days", "8-15 Days", "16-30 Days", "31-60 Days", "60+ Days"]
    risk_order = ["Low", "Medium", "High", "Critical"]
    
    base = alt.Chart(data).encode(
        x=alt.X('Bucket', sort=bucket_order, title="Aging Bucket", axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Risk', sort=risk_order, title="Risk Level"),
    )
    
    heatmap = base.mark_rect().encode(
        color=alt.Color('Count', scale=alt.Scale(range=['#1E3A5F', '#C9A227']), title="Case Count"),
        tooltip=['Risk', 'Bucket', 'Count']
    )
    
    text = base.mark_text(baseline='middle').encode(
        text='Count',
        color=alt.condition(
            alt.datum.Count > 10,
            alt.value('black'),
            alt.value('white')
        )
    )
    
    st.altair_chart((heatmap + text).properties(height=250), use_container_width=True)

def funnel_chart(df=None):
    if df is not None and not df.empty:
        cases_opened = len(df)
        # Investigations: Review, Pending Review, High Risk Open
        investigations = len(df[df['status'].isin(['Review', 'Pending Review', 'Escalated'])])
        # SAR Drafted: Draft, Pending Review
        sar_drafted = len(df[df['status'].isin(['Draft', 'Pending Review'])])
        # SAR Filed: Approved, Filed, Closed (assuming closed means done)
        sar_filed = len(df[df['status'].isin(['Approved', 'Filed'])])
        
        # Simulating upstream alerts
        alerts_generated = int(cases_opened * 2.5) 
    else:
        # Falls back to standard funnel shape if no data
        alerts_generated = 1250
        cases_opened = 420
        investigations = 280
        sar_drafted = 150
        sar_filed = 85

    funnel_data = pd.DataFrame({
        'Stage': ['Alerts Generated', 'Cases Opened', 'Investigations', 'SAR Drafted', 'SAR Filed'],
        'Value': [alerts_generated, cases_opened, investigations, sar_drafted, sar_filed],
        'SortColor': ['#2A3F55', '#2A3F55', '#2A3F55', '#C9A227', '#0D9488'] 
    })

    base = alt.Chart(funnel_data).encode(
        y=alt.Y('Stage', sort=['Alerts Generated', 'Cases Opened', 'Investigations', 'SAR Drafted', 'SAR Filed'], axis=None),
        x=alt.X('Value', axis=None, scale=alt.Scale(domain=[0, alerts_generated * 1.1]))
    )

    bar = base.mark_bar(cornerRadius=4).encode(
        color=alt.Color('SortColor', scale=None),
        tooltip=['Stage', 'Value']
    )

    text_value = base.mark_text(align='left', dx=5, color='#FFFFFF', fontWeight=600).encode(
        text='Value'
    )
    
    text_label = base.mark_text(align='right', dx=-5, color='#B0B8C1').encode(
        text='Stage'
    )

    st.altair_chart((bar + text_value + text_label).properties(height=200), use_container_width=True)

def render_lifecycle_progress(current_status):
    stages = ["Alert Generated", "Under Review", "Escalated", "SAR Drafted", "Filed", "Closed"]
    
    # Map status to stage index
    status_map = {
        "Open": 0,
        "Review": 1, "Pending Review": 1,
        "High": 2, "Critical": 2, # Assuming high risk might imply escalation if checking risk
        "Escalated": 2,
        "Draft": 3,
        "Approved": 4, "Filed": 4,
        "Closed": 5
    }
    
    current_idx = status_map.get(current_status, 0)
    
    # HTML Construction
    html = '<div style="display: flex; justify-content: space-between; align-items: center; margin: 20px 0;">'
    
    for i, stage in enumerate(stages):
        # Determine styling based on state
        if i < current_idx:
            # Completed
            color = "#0D9488" # Teal
            icon = "✓"
            weight = "600"
            opacity = "1"
        elif i == current_idx:
            # Active
            color = "#C9A227" # Gold
            icon = "●"
            weight = "700"
            opacity = "1"
        else:
            # Pending
            color = "#2A3F55" # Muted Blue/Grey
            icon = "○"
            weight = "400"
            opacity = "0.6"
            
        # Draw line logic (except for last item)
        line = ""
        if i < len(stages) - 1:
            line_color = "#0D9488" if i < current_idx else "#2A3F55"
            line = f'<div style="flex-grow: 1; height: 2px; background-color: {line_color}; margin: 0 10px;"></div>'
            
        step_html = f'''
        <div style="display: flex; flex-direction: column; align-items: center; min-width: 60px;">
            <div style="color: {color}; font-size: 1.2rem; margin-bottom: 5px;">{icon}</div>
            <div style="color: {color if i <= current_idx else '#B0B8C1'}; font-size: 0.75rem; text-align: center; font-weight: {weight}; opacity: {opacity};">{stage}</div>
        </div>
        {line}
        '''
        html += step_html
        
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Views
# -----------------------------------------------------------------------------

@st.dialog("Audit Trail & Timeline")
def handle_audit_view(case_id, row_data):
    st.markdown(f"**Case ID:** `{case_id}`")
    
    # Lifecycle Progress Bar
    current_status = row_data.get('Status', 'Open')
    render_lifecycle_progress(current_status)
    
    st.markdown("---")
    
    # Timeline
    try:
        # DB available?
        history = []
        if DB_CONNECTED:
            # Need numeric ID for query? Assuming input ID is string 'CAS-XXXX' or int
            # Our mock data uses 'CAS-XXXX' but real DB returns integers usually.
            # Let's try to parse if needed.
            try:
                numeric_id = int(str(case_id).replace('CAS-', ''))
            except:
                numeric_id = case_id
            
            history = get_case_audit_history(numeric_id)
        
        if not history:
             # Simulation Fallback
             base_time = datetime.datetime.now()
             history = [
                 {"timestamp": base_time, "user": "System", "action": "Risk Score Updated (High)", "risk_version": "v2.1", "model_version": "FinBERT-Reg-v4"},
                 {"timestamp": base_time - datetime.timedelta(hours=2), "user": "Sarah J.", "action": "Manual Review Started", "risk_version": "v2.0", "model_version": "-"},
                 {"timestamp": base_time - datetime.timedelta(hours=5), "user": "System", "action": "Case Auto-Created", "risk_version": "v2.0", "model_version": "RuleEngine-v12"}
             ]

        # Render Timeline
        for event in history:
            with st.container():
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.caption(event['timestamp'].strftime("%H:%M") if isinstance(event['timestamp'], datetime.datetime) else str(event['timestamp']))
                    st.caption(event['timestamp'].strftime("%Y-%m-%d") if isinstance(event['timestamp'], datetime.datetime) else "")
                with c2:
                    st.markdown(f"**{event['action']}**")
                    st.markdown(f"User: `{event['user']}` | Model: `{event.get('model_version', 'N/A')}`")
                    st.markdown(f"Risk Version: `{event.get('risk_version', 'N/A')}`")
                    if event.get('details'):
                        with st.expander("Details"):
                            st.text(event['details'])
                st.divider()

    except Exception as e:
        st.error(f"Could not load history: {e}")
        
    # Role-Based Action: Filing Controls
    user_role = st.session_state.get('user_role', 'Analyst')
    if user_role not in ['Analyst']:
         st.markdown("### Actions")
         c_act1, c_act2 = st.columns(2)
         with c_act1:
             if st.button("✅ Approve & File SAR", type="primary", use_container_width=True):
                 st.toast(f"SAR {case_id} Filed with FinCEN by {user_role}", icon="✅")
         with c_act2:
             if st.button("↩️ Return for Rework", use_container_width=True):
                 st.toast(f"SAR {case_id} returned to Analyst", icon="↩️")
    else:
         st.info("ℹ️ Filing controls are restricted to Reviewers and MLROs.")

@st.dialog("Risk Analysis Breakdown")
def handle_risk_view(case_id, row_data):
    st.markdown(f"### Case: `{case_id}`")
    
    # Mock Risk Data
    risk_level = row_data.get('Risk', 'High')
    risk_score = 88 if risk_level == 'High' else (65 if risk_level == 'Medium' else 25)
    confidence = 0.94
    
    # 1. Top Scores
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Risk Score", f"{risk_score}/100", delta="Critical" if risk_score > 80 else "Normal", delta_color="inverse")
    with c2: st.metric("Model Confidence", f"{int(confidence*100)}%")
    with c3: st.metric("Typologies Matches", "2")

    st.markdown("---")
    
    # 2. Feature Contributions (Altair)
    st.caption("Feature Contribution to Risk Score")
    feat_data = pd.DataFrame({
        'Feature': ['Structured Cash', 'Velocity > 3 Days', 'High Risk Geo', 'New Account', 'Round Amounts'],
        'Impact': [35, 25, 15, 10, 5]
    })
    
    bar_chart = alt.Chart(feat_data).encode(
        x=alt.X('Impact', title='Contribution Points'),
        y=alt.Y('Feature', sort='-x', title=None),
        color=alt.Color('Impact', scale=alt.Scale(scheme='reds'), legend=None),
        tooltip=['Feature', 'Impact']
    ).mark_bar().properties(height=200)
    
    st.altair_chart(bar_chart, use_container_width=True)
    
    # 3. Rules & Typologies
    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown("**Triggered Rules**")
        st.warning("⚠️ R-102: Cumulative Cash > $10k")
        st.warning("⚠️ R-205: Rapid Movement of Funds")
        st.info("ℹ️ R-001: KYC Update Recent")
        
    with c_right:
        st.markdown("**Suspected Typologies**")
        st.markdown("- **Structuring / Smurfing** (95% Match)")
        st.markdown("- **Money Laundering** (70% Match)")

    # Role-Based Action: Override Risk
    user_role = st.session_state.get('user_role', 'Analyst')
    if user_role in ['MLRO', 'Compliance Head']:
        st.markdown("---")
        st.markdown("🔒 **MLRO Controls**")
        c_risk, c_btn = st.columns([3, 1])
        with c_risk:
             new_risk = st.selectbox("Override Risk Level", ["Low", "Medium", "High", "Critical"], index=2, key=f"risk_override_{case_id}")
        with c_btn:
             st.markdown("<br>", unsafe_allow_html=True)
             if st.button("Update Risk"):
                 st.toast(f"Risk updated to {new_risk} by {user_role}", icon="🛡️")

def render_dashboard():
    # Header & Export Actions
    h_c1, h_c2 = st.columns([2, 1])
    with h_c1:
        st.title("Compliance Dashboard")
    with h_c2:
        st.markdown('<div style="display: flex; gap: 10px; justify-content: flex-end; align-items: center; height: 100%;">', unsafe_allow_html=True)
        # 1. Generate Regulatory Report (Backend)
        report_text = generate_regulatory_report()
        st.download_button(
            "📄 Gen. Report",
            data=report_text,
            file_name=f"SAR_Summary_{datetime.date.today()}.txt",
            mime="text/plain",
            help="Generate Regulatory SAR Summary Report (Text)"
        )
        
        # 2. Export Cases CSV (Frontend/Backend Logic)
        try:
             # CSV requires fetching all cases potentially
             all_cases = get_all_cases(limit=1000)
             csv_data = pd.DataFrame(all_cases).to_csv(index=False)
             st.download_button(
                 "📊 Export CSV",
                 data=csv_data,
                 file_name=f"cases_export_{datetime.date.today()}.csv",
                 mime="text/csv"
             )
        except:
             st.button("📊 Export CSV", disabled=True)

        # 3. Export PDF (Mock)
        if st.button("🖨️ PDF", help="Export Dashboard View as PDF"):
             st.toast("Processing PDF Export... (Sent to print queue)", icon="🖨️")

        st.markdown('</div>', unsafe_allow_html=True)
    
    # Check DB status
    if not DB_CONNECTED and "db_toast_shown" not in st.session_state:
        st.toast("⚠️ Database disconnected. Using Simulation Mode.", icon="⚠️")
        st.session_state.db_toast_shown = True

    # -------------------------------------------------------------------------
    # Global Filters
    # -------------------------------------------------------------------------
    with st.expander("🔍 Filter Dashboard", expanded=True):
        f_c1, f_c2, f_c3, f_c4, f_c5 = st.columns(5)
        with f_c1:
            date_range = st.date_input("Date Range", [datetime.date.today() - datetime.timedelta(days=30), datetime.date.today()])
        with f_c2:
            risk_filter = st.multiselect("Risk Level", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
        with f_c3:
            # Mock Analysts for filter as user table isn't joined yet
            analyst_filter = st.multiselect("Analyst", ["Sarah J.", "Mike R.", "David C.", "System"], default=[]) 
        with f_c4:
            typology_filter = st.multiselect("Typology", ["Structuring", "Money Laundering", "Human Trafficking"], default=[])
        with f_c5:
            status_filter = st.multiselect("Status", ["Open", "Review", "Closed", "Approved", "Draft"], default=["Open", "Review", "Draft"])
        
        apply_filters = st.button("Apply Filters", type="primary")

    # -------------------------------------------------------------------------
    # Data Fetching & Processing
    # -------------------------------------------------------------------------
    if not DB_CONNECTED:
        # SIMULATION DATA GENERATION (Used when DB is down)
        # This replaces the static mock data to allow filters to "work" visually
        mock_data = []
        base_date = datetime.datetime.now()
        analysts = ["Sarah J.", "Mike R.", "David C."]
        risks = ["High", "Medium", "Low"]
        statuses = ["Open", "Review", "Closed"]
        
        for i in range(50):
            mock_data.append({
                "id": f"CAS-{2940+i}",
                "customer_name": f"Customer {i}",
                "status": statuses[i % 3],
                "risk_level": risks[i % 3],
                "created_at": base_date - datetime.timedelta(days=i*2),
                "analyst_id": (i % 3) + 1,
                "analyst_name": analysts[i % 3], # Helpers
                "generated_narrative": "continuing activity detected" if i % 5 == 0 else "standard review",
                "typology": "Structuring" if i % 2 == 0 else "Money Laundering"
            })
        df = pd.DataFrame(mock_data)
        
    else:
        # REAL DATA FETCHING
        try:
            cases = get_all_cases(limit=1000)
            df = pd.DataFrame(cases)
            # Map Analyst IDs to Names (Mock mapping for now as we don't have user table joined)
            analyst_map = {1: "Sarah J.", 2: "Mike R.", 3: "David C."}
            if not df.empty:
                df['analyst_name'] = df['analyst_id'].map(analyst_map).fillna("System")
                # Typology extraction mock (real extraction would parse narrative)
                df['typology'] = df['generated_narrative'].apply(lambda x: "Structuring" if "structuring" in str(x).lower() else ("Money Laundering" if "laundering" in str(x).lower() else "General"))
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            df = pd.DataFrame()

    # -------------------------------------------------------------------------
    # Filter Logic
    # -------------------------------------------------------------------------
    if not df.empty:
        # Date Filter
        if len(date_range) == 2:
            start_date, end_date = date_range
            # Ensure created_at is datetime
            if not pd.api.types.is_datetime64_any_dtype(df['created_at']):
                 df['created_at'] = pd.to_datetime(df['created_at'])
            
            mask = (df['created_at'].dt.date >= start_date) & (df['created_at'].dt.date <= end_date)
            df = df.loc[mask]

        # Dropdown Filters
        if risk_filter:
            df = df[df['risk_level'].isin(risk_filter)]
        if analyst_filter:
            df = df[df['analyst_name'].isin(analyst_filter)]
        if typology_filter: 
             # Basic substring match simulation for typology
             df = df[df['typology'].isin(typology_filter)]
        if status_filter:
            df = df[df['status'].isin(status_filter)]

    # -------------------------------------------------------------------------
    # KPIs Calculation (Dynamic)
    # -------------------------------------------------------------------------
    
    # Defaults
    metrics = {
        "sar_filed_month": 0,
        "avg_time_to_file": 0,
        "sla_breach_pct": 0.0,
        "backlog_30_days": 0,
        "continuing_sar": 0
    }

    if not df.empty:
        current_month = datetime.datetime.now().month
        current_year = datetime.datetime.now().year
        
        # SAR Filed Month (Count rows created this month)
        metrics["sar_filed_month"] = len(df[
            (df['created_at'].dt.month == current_month) & 
            (df['created_at'].dt.year == current_year)
        ])
        
        # Avg Time to File (Mocked calculation: random variation based on row count)
        # Real logic would need 'closed_at' which isn't in schema yet
        metrics["avg_time_to_file"] = round(12.5 + (len(df) % 3), 1)

        # SLA Breach (Open > 30 days)
        now = pd.Timestamp.now()
        breaches = df[
            (df['status'] != 'Closed') & 
            (df['status'] != 'Approved') &
            (df['created_at'] < (now - pd.Timedelta(days=30)))
        ]
        metrics["backlog_30_days"] = len(breaches)
        if len(df) > 0:
            metrics["sla_breach_pct"] = round((len(breaches) / len(df)) * 100, 1)
        
        # Continuing SARs
        if 'generated_narrative' in df.columns:
            continuing = df[df['generated_narrative'].astype(str).str.contains('continuing', case=False, na=False)]
            metrics["continuing_sar"] = len(continuing)

    # 0. Top Level KPIs (Rendered)
    t_c1, t_c2, t_c3, t_c4, t_c5 = st.columns(5)
    with t_c1: kpi_card("SAR Filed (Period)", f"{metrics['sar_filed_month']}", "+12%", "good")
    with t_c2: kpi_card("Avg File Time", f"{metrics['avg_time_to_file']} Days", "-1.5 Days", "good")
    with t_c3: kpi_card("SLA Breach %", f"{metrics['sla_breach_pct']}%", "+0.5%", "bad")
    with t_c4: kpi_card("Backlog > 30 Days", f"{metrics['backlog_30_days']}", "-2", "good")
    with t_c5: kpi_card("Continuing SARs", f"{metrics['continuing_sar']}", "+3", "bad")

    st.markdown("<div style='margin-bottom: 20px'></div>", unsafe_allow_html=True)
    
    # 1. Metrics (Second Row - Aggregates from Filtered Data)
    total_cases_count = len(df)
    high_risk_count = len(df[df['risk_level'] == 'High'])
    pending_count = len(df[df['status'].isin(['Review', 'Pending Review'])])
    flagged_count = len(df[df['risk_level'].isin(['High', 'Critical'])]) # Proxy

    col1, col2, col3, col4 = st.columns(4)
    with col1: kpi_card("Total Cases", f"{total_cases_count}", None, "good")
    with col2: kpi_card("High Risk Cases", f"{high_risk_count}", None, "bad")
    with col3: kpi_card("Pending Review", f"{pending_count}", None, "good")
    with col4: kpi_card("Flagged Alerts", f"{flagged_count}", None, "bad")

    st.write("")
    
    # 2. Charts & Activity
    m_col1, m_col2 = st.columns([2, 1])
    with m_col1:
        st.markdown('<div class="content-card"><div class="card-header">Recent Activity</div>', unsafe_allow_html=True)
        
        if not df.empty:
            # Display Table with limited columns
            display_df = df[['id', 'analyst_name', 'risk_level', 'status', 'created_at']].copy()
            display_df.columns = ['ID', 'Analyst', 'Risk', 'Status', 'Date']
            
            # Add Action Column for "View Risk Breakdown"
            display_df['Risk Breakdown'] = False
            # Add Action Column for "Audit View"
            display_df['Audit View'] = False
            
            # Use Data Editor
            edited_df = st.data_editor(
                display_df.head(10), # Show top 10
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Risk Breakdown": st.column_config.CheckboxColumn(
                        "Risk Details",
                        help="View detailed risk analysis",
                        default=False,
                    ),
                     "Audit View": st.column_config.CheckboxColumn(
                        "Audit Trail",
                        help="View timeline and history",
                        default=False,
                    )
                },
                disabled=['ID', 'Analyst', 'Risk', 'Status', 'Date'],
                key="case_table_editor"
            )
            
            # Interaction Logic
            # 1. Check for Checkbox Click (Risk View)
            risk_triggered = edited_df[edited_df['Risk Breakdown'] == True]
            if not risk_triggered.empty:
                 row = risk_triggered.iloc[0]
                 handle_risk_view(row['ID'], row)
                 
            # 2. Check for Checkbox Click (Audit View)
            elif not edited_df[edited_df['Audit View'] == True].empty:
                audit_triggered = edited_df[edited_df['Audit View'] == True]
                row = audit_triggered.iloc[0]
                handle_audit_view(row['ID'], row)

        else:
            st.info("No cases match the selected filters.")
            
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Funnel Chart Row
        st.markdown('<div class="content-card"><div class="card-header">Conversion Funnel</div>', unsafe_allow_html=True)
        funnel_chart(df if not df.empty else None)
        st.markdown('</div>', unsafe_allow_html=True)

    with m_col2:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Risk Distribution</div>', unsafe_allow_html=True)
        
        # Aggregate Risk for Chart
        if not df.empty:
            risk_counts = df['risk_level'].value_counts().reset_index()
            risk_counts.columns = ['Risk Level', 'Cases']
            risk_chart(risk_counts)
        else:
            st.info("No data")
            
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Case Aging Heatmap</div>', unsafe_allow_html=True)
        if not df.empty:
             # Convert filtered DF back to list of dicts for the helper function if needed, 
             # OR update helper to accept DF.
             # Helper expects list of dicts currently.
             valid_records = df[['created_at', 'risk_level']].to_dict('records')
             case_aging_heatmap(valid_records)
        else:
             case_aging_heatmap(None)
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
                        st.markdown(f'<div style="background-color:#1E3A5F; border-left:4px solid #C9A227; padding:15px; border-radius:4px; color:#FFFFFF;">{narrative}</div>', unsafe_allow_html=True)
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
        st.markdown('<div style="font-size: 1.2rem; font-weight: 700; color: #C9A227; margin-bottom: 20px;">RegIntel Suite</div>', unsafe_allow_html=True)
        st.caption(f"User: {st.session_state.user_email}")
        st.caption(f"Role: {st.session_state.get('user_role', 'Analyst')}")
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
