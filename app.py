import streamlit as st
import pandas as pd
import datetime
import altair as alt

from supabase import create_client, Client

# ---- Supabase Config ----
SUPABASE_URL = "https://cwyvjesaxmcidlsceigj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN3eXZqZXNheG1jaWRsc2NlaWdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE3MjU3NjUsImV4cCI6MjA2NzMwMTc2NX0.dlKjz0NEY-EHo2au01wpwa6OPb48ly8swrJ7WqHo5Hg"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- Helper: Get logged-in user ID ----
def get_user_id():
    user = st.session_state.get("user")
    if user:
        return user.id
    return None

# ---- Login/Signup ----
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
                    res = supabase.auth.sign_up({"email": email, "password": password})
                    st.success("✅ Account created! Verify email before logging in.")
                else:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    if res.user:
                        st.session_state.user = res.user

                        # ⬇️ Fetch budgets + expenses
                        user_id = get_user_id()
                        budgets = supabase.table("budgets").select("*").eq("user_id", user_id).execute()
                        st.session_state.food_budgets = {
                            row["place"]: row["budget_amount"] for row in budgets.data
                        } if budgets.data else {}

                        expenses = supabase.table("expenses").select("*").eq("user_id", user_id).execute()
                        st.session_state.food_expenses = expenses.data if expenses.data else []

                        st.experimental_rerun()
                    else:
                        st.error("❌ Login failed. Try again.")
            except Exception:
                st.error("Something went wrong. Try again.")
    st.stop()

# ---- Setup session state ----
if "food_budgets" not in st.session_state:
    st.session_state.food_budgets = {}

if "food_expenses" not in st.session_state:
    st.session_state.food_expenses = []

# ---- Main App ----
st.set_page_config(page_title="Food Expense Tracker", layout="wide")
st.title("🍽️ Campus Food Expense Tracker")

food_places = ['Amul','Just Chill', 'Tapri', 'Dawat', 'GoInsta', '2D', 'TeaPost', 'South Point', 'Atul Bakery', 'Krupa General', 'Hunger Games', 'Mahavir', 'Outside Restaurant Visit', 'Online food delivery']

# ---- Budget Input ----
st.sidebar.header("Set Weekly Budgets")
for place in food_places:
    existing = st.session_state.food_budgets.get(place, 0)
    budget = st.sidebar.number_input(f"{place} Budget", min_value=0, step=50, value=existing, key=f"budget_{place}")
    if budget > 0 and get_user_id():
        user_id = get_user_id()
        existing_row = supabase.table("budgets").select("*").eq("user_id", user_id).eq("place", place).execute()
        if existing_row.data:
            supabase.table("budgets").update({"budget_amount": budget}).eq("id", existing_row.data[0]["id"]).execute()
        else:
            supabase.table("budgets").insert({
                "user_id": user_id,
                "place": place,
                "budget_amount": budget
            }).execute()
        st.session_state.food_budgets[place] = budget

# ---- Add Expense ----
st.header("💸 Add Food Expense")
with st.form("add_expense"):
    place = st.selectbox("Food Place", food_places)
    amount = st.slider("Amount Spent", min_value=10, max_value=1000, step=10)
    note = st.text_input("Note (optional)")
    date = st.date_input("Date", value=datetime.date.today())
    time = st.time_input("Time", value=datetime.datetime.now().time())
    timestamp = datetime.datetime.combine(date, time).strftime("%d-%m-%Y %H:%M:%S")
    submit = st.form_submit_button("Add Expense")

    if submit and get_user_id():
        supabase.table("expenses").insert({
            "user_id": get_user_id(),
            "place": place,
            "amount": amount,
            "note": note,
            "timestamp": timestamp
        }).execute()

        # Update session state
        expenses = supabase.table("expenses").select("*").eq("user_id", get_user_id()).execute()
        st.session_state.food_expenses = expenses.data if expenses.data else []

        st.success(f"Added ₹{amount} at {place} on {timestamp}")

# ---- Expense History ----
if st.session_state.food_expenses:
    df = pd.DataFrame(st.session_state.food_expenses)
    st.header("📜 Expense History")
    st.dataframe(df)

    # ---- Budget Alerts ----
    st.header("🚨 Budget Alerts")
    df_grouped = df.groupby("place")["amount"].sum().reset_index()
    for _, row in df_grouped.iterrows():
        place = row["place"]
        spent = row["amount"]
        budget = st.session_state.food_budgets.get(place)
        if budget and spent > budget:
            st.warning(f"⚠️ Overspent at {place} by ₹{int(spent - budget)}")

    # ---- Dashboard ----
    st.header("📊 Dashboard")
    df_grouped["percentage"] = (df_grouped["amount"] / df_grouped["amount"].sum() * 100).round(2)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Spending by Place")
        bar_chart = alt.Chart(df_grouped).mark_bar().encode(
            x="place",
            y="amount",
            tooltip=["place", "amount"]
        ).properties(width=400, height=300)
        st.altair_chart(bar_chart)

    with col2:
        st.subheader("Spending Distribution")
        pie_chart = alt.Chart(df_grouped).mark_arc().encode(
            theta="amount",
            color="place",
            tooltip=["place", "amount", "percentage"]
        ).properties(width=400, height=300)
        st.altair_chart(pie_chart)

    # ---- Summary ----
    st.header("📌 Summary")
    st.success(f"Total Spent: ₹{df['amount'].sum()}")
else:
    st.info("No expenses yet. Add one above!")