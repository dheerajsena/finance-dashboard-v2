import streamlit as st
from datetime import datetime
import pandas as pd
import json
import uuid
import os
import plotly.graph_objects as go

# --- Helper Paths ---
GOALS_FILE = "data/goals.json"
SAVINGS_FILE = "data/savings.csv"

# --- Ensure Directories ---
os.makedirs("data", exist_ok=True)

# --- Load or Init Goals ---
if os.path.exists(GOALS_FILE):
    with open(GOALS_FILE, "r") as f:
        goals = json.load(f)
else:
    goals = []

# --- Load or Init Savings Log ---
if os.path.exists(SAVINGS_FILE):
    savings_log = pd.read_csv(SAVINGS_FILE)
else:
    savings_log = pd.DataFrame(columns=["date", "amount", "source", "goal_id", "notes"])

# --- Title ---
st.title("💸 Personal Finance Goal Tracker – v3")

# --- Section 1: Income & Expense Setup ---
st.sidebar.header("🔧 Monthly Settings")
gross_income = st.sidebar.number_input("Gross Annual Salary (AUD)", 60000, 250000, 105000, step=5000)
tax_rate = 0.30
monthly_income = (gross_income * (1 - tax_rate)) / 12
monthly_expense = st.sidebar.number_input("Monthly Expenses (AUD)", 1000, 10000, 3200, step=100)

monthly_surplus = monthly_income - monthly_expense
st.sidebar.markdown(f"💰 **Estimated Monthly Surplus**: ${monthly_surplus:,.2f}")

# --- Section 2: Goal Manager ---
st.header("🎯 Your Financial Goals")
with st.expander("➕ Add New Goal"):
    goal_name = st.text_input("Goal Name")
    target_amount = st.number_input("Target Amount (AUD)", min_value=500.0)
    timeline_months = st.slider("Timeline (Months)", 1, 36, 6)
    priority = st.slider("Priority (%)", 0, 100, 50)
    if st.button("Add Goal"):
        new_goal = {
            "id": str(uuid.uuid4()),
            "name": goal_name,
            "target_amount": target_amount,
            "timeline_months": timeline_months,
            "priority": priority,
            "start_date": datetime.today().strftime("%Y-%m-%d")
        }
        goals.append(new_goal)
        with open(GOALS_FILE, "w") as f:
            json.dump(goals, f)
        st.success("Goal added!")

# --- Section 3: Display Goals & Progress ---
for goal in goals:
    goal_id = goal["id"]
    st.subheader(f"📌 {goal['name']}")
    goal_savings = savings_log[savings_log["goal_id"] == goal_id]["amount"].sum()
    remaining = goal["target_amount"] - goal_savings
    monthly_required = goal["target_amount"] / goal["timeline_months"]
    months_to_goal = remaining / monthly_surplus if monthly_surplus > 0 else float("inf")

    st.markdown(
        f"- Target: **${goal['target_amount']:,.2f}**\n"
        f"- Saved: **${goal_savings:,.2f}**\n"
        f"- Remaining: **${remaining:,.2f}**\n"
        f"- Required Monthly Contribution: **${monthly_required:,.2f}**\n"
        f"- Estimated Months to Goal (at current pace): **{months_to_goal:.1f} months**"
    )

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=(goal_savings / goal["target_amount"]) * 100 if goal["target_amount"] > 0 else 0,
        gauge={"axis": {"range": [0, 100]}},
        title={"text": f"Progress to {goal['name']}"}
    ))
    st.plotly_chart(fig, use_container_width=True)

# --- Section 4: Savings Entry ---
st.header("💾 Add to Your Savings Pool")
with st.form("savings_form"):
    date = st.date_input("Date", value=datetime.today())
    amount = st.number_input("Amount Saved (AUD)", min_value=0.0)
    source = st.text_input("Source (salary, bonus, freelance...)")
    notes = st.text_input("Optional Notes")
    goal_selected = st.selectbox("Select Goal", options=[(g["id"], g["name"]) for g in goals], format_func=lambda x: x[1])
    submitted = st.form_submit_button("Log This Saving")
    if submitted:
        new_row = {
            "date": date.strftime("%Y-%m-%d"),
            "amount": amount,
            "source": source,
            "goal_id": goal_selected[0],
            "notes": notes
        }
        savings_log = savings_log.append(new_row, ignore_index=True)
        savings_log.to_csv(SAVINGS_FILE, index=False)
        st.success("Saving logged successfully!")

# --- Section 5: Full History ---
st.header("📜 Your Savings Log")
st.dataframe(savings_log.sort_values("date", ascending=False))