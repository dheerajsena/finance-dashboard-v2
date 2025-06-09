import streamlit as st
from datetime import datetime
import pandas as pd
import json
import uuid
import os
import plotly.graph_objects as go

# --- Paths ---
GOALS_FILE = "data/goals.json"
SAVINGS_FILE = "data/savings.csv"

# --- Init Storage ---
os.makedirs("data", exist_ok=True)
if not os.path.exists(GOALS_FILE):
    with open(GOALS_FILE, "w") as f:
        json.dump([], f)
if not os.path.exists(SAVINGS_FILE):
    pd.DataFrame(columns=["date", "amount", "source", "goal_id", "notes"]).to_csv(SAVINGS_FILE, index=False)

# --- Load Data ---
with open(GOALS_FILE, "r") as f:
    goals = json.load(f)
savings_log = pd.read_csv(SAVINGS_FILE)

# --- App Title ---
st.set_page_config(layout="wide")
st.title("🧠 Finance App v4 – AI Personal CFO")

# --- Sidebar: Income & Expenses ---
st.sidebar.header("🛠️ Monthly Settings")
gross_income = st.sidebar.number_input("Gross Salary (AUD, incl. Super)", 60000, 250000, 105000, step=5000)
monthly_expense = st.sidebar.number_input("Monthly Expenses (AUD)", 1000, 10000, 3200, step=100)
tax_rate = 0.30
monthly_income = (gross_income * (1 - tax_rate)) / 12
monthly_surplus = monthly_income - monthly_expense
st.sidebar.markdown(f"💡 **Estimated Surplus:** ${monthly_surplus:,.2f}")

# --- Goal Summary Dashboard ---
st.header("📊 Overview: Your Goals & Progress")
if goals:
    goal_data = []
    for g in goals:
        goal_id = g["id"]
        goal_savings = savings_log[savings_log["goal_id"] == goal_id]["amount"].sum()
        percent = round((goal_savings / g["target_amount"]) * 100, 1)
        months_remaining = g["timeline_months"]
        needed = g["target_amount"] - goal_savings
        monthly_required = g["target_amount"] / g["timeline_months"]
        est_time = needed / monthly_surplus if monthly_surplus > 0 else float("inf")
        goal_data.append([g["name"], g["target_amount"], goal_savings, percent, g["timeline_months"], est_time])

    df_goals = pd.DataFrame(goal_data, columns=["Goal", "Target", "Saved", "% Complete", "Timeline (mo)", "Est. Time @ Pace"])
    st.dataframe(df_goals)
else:
    st.info("No goals yet. Add one below.")

# --- Add/Edit/Delete Goal ---
st.subheader("🎯 Manage Goals")
with st.expander("➕ Add New Goal"):
    name = st.text_input("Goal Name")
    target = st.number_input("Target Amount", 500.0)
    months = st.slider("Timeline in Months", 1, 36, 6)
    prio = st.slider("Priority Weight (%)", 1, 100, 50)
    if st.button("Add Goal"):
        goals.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "target_amount": target,
            "timeline_months": months,
            "priority": prio,
            "start_date": datetime.today().strftime("%Y-%m-%d")
        })
        with open(GOALS_FILE, "w") as f:
            json.dump(goals, f)
        st.success("Goal added. Refresh to see updates.")

if goals:
    goal_options = {g["name"]: g["id"] for g in goals}
    with st.expander("🧹 Delete a Goal"):
        to_del = st.selectbox("Choose Goal to Delete", list(goal_options.keys()))
        if st.button("Delete Goal"):
            goals = [g for g in goals if g["id"] != goal_options[to_del]]
            with open(GOALS_FILE, "w") as f:
                json.dump(goals, f)
            st.warning(f"Goal '{to_del}' deleted. Refresh to update.")

# --- Add Savings Entry ---
st.header("💾 Log New Saving")
with st.form("save_form"):
    date = st.date_input("Date", datetime.today())
    amount = st.number_input("Amount (AUD)", 0.0)
    source = st.text_input("Source (e.g. salary, bonus...)")
    notes = st.text_input("Notes")
    goal_name = st.selectbox("Which Goal?", options=list(goal_options.keys()) if goals else [])
    submitted = st.form_submit_button("Log Saving")
    if submitted and goal_name:
        row = {
            "date": date.strftime("%Y-%m-%d"),
            "amount": amount,
            "source": source,
            "goal_id": goal_options[goal_name],
            "notes": notes
        }
        savings_log = savings_log.append(row, ignore_index=True)
        savings_log.to_csv(SAVINGS_FILE, index=False)
        st.success("Saved!")

# --- Show History ---
st.header("📜 Savings History")
st.dataframe(savings_log.sort_values("date", ascending=False))

# --- Charts ---
st.header("📈 Visual Progress")
for g in goals:
    goal_id = g["id"]
    saved = savings_log[savings_log["goal_id"] == goal_id]["amount"].sum()
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=(saved / g["target_amount"]) * 100 if g["target_amount"] > 0 else 0,
        gauge={"axis": {"range": [0, 100]}},
        title={"text": f"{g['name']} Completion"}
    ))
    st.plotly_chart(fig, use_container_width=True)