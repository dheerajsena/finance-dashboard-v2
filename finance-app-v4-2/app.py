import streamlit as st
import pandas as pd
import json
import uuid
import os
from datetime import datetime
import plotly.graph_objects as go

# ── Constants & Paths ──────────────────────────────────────────────────────────
DATA_DIR      = "data"
GOALS_FILE    = os.path.join(DATA_DIR, "goals.json")
SAVINGS_FILE  = os.path.join(DATA_DIR, "savings.csv")

# ── CACHED I/O ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_goals():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(GOALS_FILE):
        with open(GOALS_FILE, "w") as f:
            json.dump([], f)
    with open(GOALS_FILE, "r") as f:
        return json.load(f)

@st.cache_data
def load_savings():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(SAVINGS_FILE):
        pd.DataFrame(columns=["date","amount","source","goal_id","notes"])\
          .to_csv(SAVINGS_FILE, index=False)
    return pd.read_csv(SAVINGS_FILE, parse_dates=["date"])

def save_goals(goals):
    with open(GOALS_FILE, "w") as f:
        json.dump(goals, f)
    load_goals.clear()  # clear cache

def save_savings(df):
    df.to_csv(SAVINGS_FILE, index=False)
    load_savings.clear()  # clear cache

# ── APP CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Personal CFO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Load Data ─────────────────────────────────────────────────────────────────
goals      = load_goals()        # list of dicts
savings_df = load_savings()      # DataFrame

# ── SIDEBAR: GLOBAL SETTINGS ───────────────────────────────────────────────────
st.sidebar.header("🛠️ Settings & Cashflow")
salary       = st.sidebar.number_input("Gross Annual Salary (AUD)", 60_000, 300_000, 105_000, step=5_000)
expenses     = st.sidebar.number_input("Monthly Expenses (AUD)",      500,    10_000,   3_200, step=100)
tax_rate     = 0.30
net_monthly  = (salary * (1 - tax_rate)) / 12
surplus      = net_monthly - expenses
st.sidebar.markdown(f"**Net Income**: ${net_monthly:,.2f}")
st.sidebar.markdown(f"**Surplus**:    ${surplus:,.2f}")

# ── TABS ───────────────────────────────────────────────────────────────────────
tabs = st.tabs(["🏠 Overview", "🎯 Goals", "💾 Savings", "📄 Reports"])

# ── TAB 1: OVERVIEW ─────────────────────────────────────────────────────────────
with tabs[0]:
    st.header("📊 Financial Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Net Monthly Income", f"${net_monthly:,.2f}")
    col2.metric("Monthly Expenses",     f"${expenses:,.2f}")
    col3.metric("Est. Surplus",          f"${surplus:,.2f}")
    # Compute total targets & progress
    total_target = sum(g["target_amount"] for g in goals)
    total_saved  = savings_df["amount"].sum()
    pct_total    = (total_saved/total_target*100) if total_target>0 else 0
    col4.metric("Overall Progress", f"{pct_total:.1f}%")
    # Summary gauge
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct_total,
        gauge={"axis":{"range":[0,100]}},
        title={"text":"Total Goal Progress"}
    ))
    st.plotly_chart(gauge, use_container_width=True)

# ── TAB 2: GOALS ────────────────────────────────────────────────────────────────
with tabs[1]:
    st.header("🎯 Manage Your Goals")
    # — Add / Edit Form —
    with st.expander("➕ Add a New Goal", expanded=True):
        with st.form("goal_form", clear_on_submit=True):
            name    = st.text_input("Name")
            amount  = st.number_input("Target Amount (AUD)", min_value=100.0, step=100.0)
            months  = st.slider("Timeline (Months)", 1, 36, 6)
            prio    = st.slider("Priority (%)", 1, 100, 50)
            submitted = st.form_submit_button("Add Goal")
            if submitted:
                new_goal = {
                    "id": str(uuid.uuid4()),
                    "name": name,
                    "target_amount": amount,
                    "timeline_months": months,
                    "priority": prio,
                    "start_date": datetime.today().strftime("%Y-%m-%d")
                }
                goals.append(new_goal)
                save_goals(goals)
                st.success(f"Goal '{name}' added!")
    # — Goal Table with Edit/Delete —
    if goals:
        df = pd.DataFrame(goals)
        df_display = df[["name","target_amount","timeline_months","priority","start_date"]]
        df_display.columns = ["Name","Target","Timeline (mo)","Priority %","Start Date"]
        st.dataframe(df_display, use_container_width=True)
        # Inline delete
        to_delete = st.selectbox("Delete a Goal", [""] + df["name"].tolist())
        if to_delete:
            if st.button("Delete Selected Goal"):
                goals[:] = [g for g in goals if g["name"]!=to_delete]
                save_goals(goals)
                st.warning(f"Deleted '{to_delete}'")
    else:
        st.info("No goals yet — use the form above to add one.")

# ── TAB 3: SAVINGS ─────────────────────────────────────────────────────────────
with tabs[2]:
    st.header("💾 Log Savings Contributions")
    # — Entry Form —
    with st.form("save_form", clear_on_submit=True):
        date   = st.date_input("Date", datetime.today())
        amt    = st.number_input("Amount Saved (AUD)", min_value=0.0, step=50.0)
        src    = st.text_input("Source (salary, bonus, etc.)")
        note   = st.text_input("Notes")
        goal_nm = st.selectbox("For Goal", [g["name"] for g in goals])
        ok     = st.form_submit_button("Log Saving")
        if ok:
            gid = next(g["id"] for g in goals if g["name"]==goal_nm)
            new_row = {"date":date, "amount":amt, "source":src, "goal_id":gid, "notes":note}
            savings_df = pd.concat([savings_df, pd.DataFrame([new_row])], ignore_index=True)
            save_savings(savings_df)
            st.success(f"Logged ${amt:,.2f} to '{goal_nm}'")
    # — History & Download —
    st.subheader("History & Export")
    st.dataframe(savings_df.sort_values("date", ascending=False), use_container_width=True)
    csv = savings_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Savings Log as CSV", data=csv, file_name="savings_log.csv")

# ── TAB 4: REPORTS ─────────────────────────────────────────────────────────────
with tabs[3]:
    st.header("📄 Monthly PDF Summary")
    month = st.selectbox("Select Month", sorted(savings_df["date"].dt.to_period("M").astype(str).unique(), reverse=True))
    if st.button("Generate PDF"):
        # Placeholder for PDF generation logic
        st.info("PDF generation is coming soon! 🚧")

# ── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("© 2025 AI Personal CFO • Built with Streamlit")
