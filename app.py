import streamlit as st
import pandas as pd
import datetime
import altair as alt
from supabase import create_client, Client

# Supabase Config
SUPABASE_URL = "https://cwyvjesaxmcidlsceigj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN3eXZqZXNheG1jaWRsc2NlaWdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE3MjU3NjUsImV4cCI6MjA2NzMwMTc2NX0.dlKjz0NEY-EHo2au01wpwa6OPb48ly8swrJ7WqHo5Hg"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Helper
def get_user_id():
    user = st.session_state.get("user")
    return user.id if user else None

# Week start checker
def is_new_week():
    today = datetime.date.today()
    return today.weekday() == 0  # Monday

# Login logic
if "user" not in st.session_state:
    st.title("🔐 Welcome to Campus Food Expense Tracker")
    auth_mode = st.radio("Choose Action", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button(auth_mode):
        if len(password) < 6:
            st.error("Password must be at least 6 characters")
        else:
            try:
                if auth_mode == "Sign Up":
                    supabase.auth.sign_up({"email": email, "password": password})
                    st.success("✅ Account created! Verify email.")
                else:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    if res.user:
                        st.session_state.user = res.user

                        # Fetch budgets
                        uid = get_user_id()
                        budgets = supabase.table("budgets").select("*").eq("user_id", uid).execute()
                        st.session_state.food_budgets = {r["place"]: r["budget_amount"] for r in budgets.data} if budgets.data else {}

                        # Fetch expenses
                        expenses = supabase.table("expenses").select("*").eq("user_id", uid).execute()
                        st.session_state.food_expenses = expenses.data if expenses.data else []

                        st.experimental_rerun()
                    else:
                        st.error("❌ Login failed.")
            except:
                st.error("Something went wrong. Try again.")
    st.stop()

# Init state
if "food_budgets" not in st.session_state:
    st.session_state.food_budgets = {}
if "food_expenses" not in st.session_state:
    st.session_state.food_expenses = []

# Weekly budget reset
if is_new_week() and get_user_id():
    uid = get_user_id()
    if st.session_state.food_budgets:
        for place, amount in st.session_state.food_budgets.items():
            supabase.table("budget_history").insert({
                "user_id": uid,
                "place": place,
                "amount": amount,
                "week_start": datetime.date.today().isoformat()
            }).execute()
    supabase.table("budgets").delete().eq("user_id", uid).execute()
    st.session_state.food_budgets = {}

# Layout
st.set_page_config(page_title="Food Expense Tracker", layout="wide")
st.title("🍽️ Campus Food Expense Tracker")

food_places = ['Amul','Just Chill', 'Tapri', 'Dawat', 'GoInsta', '2D', 'TeaPost', 'South Point', 'Atul Bakery', 'Krupa General', 'Hunger Games', 'Mahavir', 'Outside Restaurant Visit', 'Online food delivery']

# --- Sidebar Budgets ---
st.sidebar.header("Set Weekly Budgets")
for place in food_places:
    current = st.session_state.food_budgets.get(place, 0)
    budget = st.sidebar.number_input(f"{place} Budget", min_value=0, step=50, value=current, key=f"budget_{place}")
    if budget > 0 and get_user_id():
        existing = supabase.table("budgets").select("*").eq("user_id", get_user_id()).eq("place", place).execute()
        if existing.data:
            supabase.table("budgets").update({"budget_amount": budget}).eq("id", existing.data[0]["id"]).execute()
        else:
            supabase.table("budgets").insert({
                "user_id": get_user_id(),
                "place": place,
                "budget_amount": budget
            }).execute()
        st.session_state.food_budgets[place] = budget

# --- Clear Data Option ---
if st.sidebar.button("🧹 Clear ALL Data"):
    uid = get_user_id()
    supabase.table("budgets").delete().eq("user_id", uid).execute()
    supabase.table("expenses").delete().eq("user_id", uid).execute()
    st.session_state.food_budgets = {}
    st.session_state.food_expenses = []
    st.success("✅ Data cleared.")

# --- Add Expense ---
st.header("💸 Add Expense")
with st.form("add_expense"):
    place = st.selectbox("Where?", food_places)
    amount = st.slider("Amount", 10, 1000, step=10)
    note = st.text_input("Note (optional)")
    date = st.date_input("Date", value=datetime.date.today())
    time_str = st.text_input("Time (HH:MM)", value="12:00")
    try:
        time = datetime.datetime.strptime(time_str, "%H:%M").time()
        timestamp = datetime.datetime.combine(date, time).strftime("%d-%m-%Y %H:%M:%S")
    except:
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    submit = st.form_submit_button("Add")
    if submit and get_user_id():
        supabase.table("expenses").insert({
            "user_id": get_user_id(),
            "timestamp": timestamp,
            "place": place,
            "note": note,
            "amount": amount
        }).execute()
        res_exp = supabase.table("expenses").select("*").eq("user_id", get_user_id()).order("timestamp", desc=True).execute()
        st.session_state.food_expenses = res_exp.data
        st.success(f"Added ₹{amount} at {place} on {timestamp}")

# --- Display History ---
if st.session_state.food_expenses:
    df = pd.DataFrame(st.session_state.food_expenses)
    df = df.drop(columns=["id", "user_id"], errors="ignore")  # ✅ Hide IDs
    st.header("📜 Expense History")
    st.dataframe(df)

    # --- Alerts ---
    st.header("🚨 Budget Alerts")
    grouped = df.groupby("place")["amount"].sum().reset_index()
    for _, row in grouped.iterrows():
        place = row["place"]
        spent = row["amount"]
        budget = st.session_state.food_budgets.get(place)
        if budget and spent > budget:
            st.warning(f"⚠️ Overspent at **{place}** by ₹{int(spent - budget)}")

    # --- Charts ---
    st.header("📊 Dashboard")
    grouped["percentage"] = (grouped["amount"] / grouped["amount"].sum() * 100).round(2)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Spending by Place")
        st.altair_chart(alt.Chart(grouped).mark_bar().encode(
            x="place", y="amount",
            tooltip=["place", "amount"]
        ).properties(width=400, height=300))

    with col2:
        st.subheader("Spending Distribution")
        st.altair_chart(alt.Chart(grouped).mark_arc().encode(
            theta="amount", color="place",
            tooltip=["place", "amount", "percentage"]
        ).properties(width=400, height=300))

    # --- Summary ---
    st.header("📌 Summary")
    st.success(f"Total Spent: ₹{int(df['amount'].sum())}")
else:
    st.info("No expenses yet. Add some!")

