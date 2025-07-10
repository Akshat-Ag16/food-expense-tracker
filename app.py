import streamlit as st
import pandas as pd
import datetime
import altair as alt
from supabase import create_client, Client

# ---------- Supabase Setup ----------
SUPABASE_URL = "https://cwyvjesaxmcidlsceigj.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY"  # Replace this with your real key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Helpers ----------
def get_user_id():
    user = st.session_state.get("user")
    return user.id if user else None

def load_user_data():
    uid = get_user_id()
    if uid:
        budgets = supabase.table("budgets").select("*").eq("user_id", uid).execute()
        expenses = supabase.table("expenses").select("*").eq("user_id", uid).order("timestamp", desc=True).execute()

        st.session_state.food_budgets = {
            row["place"]: row["budget_amount"] for row in budgets.data
        } if budgets.data else {}

        st.session_state.food_expenses = expenses.data if expenses.data else []

# ---------- Login ----------
if "user" not in st.session_state:
    st.title("🔐 Campus Food Expense Tracker")
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
                    st.success("Account created! Please verify your email before logging in.")
                else:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    if res.session and res.user:
                        st.session_state.user = res.user
                        st.experimental_rerun()
                    else:
                        st.error("Login failed. Try again.")
            except Exception as e:
                st.error(f"Something went wrong: {e}")
    st.stop()

# ---------- Load Data After Login ----------
if "food_budgets" not in st.session_state or "food_expenses" not in st.session_state:
    load_user_data()

# ---------- App Body ----------
food_places = ['Amul','Just Chill', 'Tapri', 'Dawat', 'GoInsta', '2D', 'TeaPost', 'South Point',
               'Atul Bakery', 'Krupa General', 'Hunger Games', 'Mahavir', 'Outside Restaurant Visit',
               'Online food delivery']

# ---------- Weekly Budgets ----------
st.header("💰 Weekly Budgets")
for place in food_places:
    current = st.session_state.food_budgets.get(place, 0)
    budget = st.number_input(f"{place} Budget", min_value=0, step=50, value=current, key=f"budget_{place}")
    if budget > 0:
        existing = supabase.table("budgets").select("*").eq("user_id", get_user_id()).eq("place", place).execute()
        if existing.data:
            supabase.table("budgets").update({"budget_amount": budget}).eq("id", existing.data[0]["id"]).execute()
        else:
            supabase.table("budgets").insert({"user_id": get_user_id(), "place": place, "budget_amount": budget}).execute()
        st.session_state.food_budgets[place] = budget

# ---------- Add Expense ----------
st.header("🧾 Add Expense")
with st.form("expense_form"):
    place = st.selectbox("Place", food_places)
    amount = st.slider("Amount Spent", 10, 1000, step=10)
    note = st.text_input("Note (optional)")
    date = st.date_input("Date", value=datetime.date.today())
    time_str = st.text_input("Time (HH:MM)", value="12:00")

    try:
        time = datetime.datetime.strptime(time_str, "%H:%M").time()
        timestamp = datetime.datetime.combine(date, time).strftime("%d-%m-%Y %H:%M:%S")
    except:
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    submit = st.form_submit_button("Add Expense")

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

# ---------- Expense History ----------
st.header("📜 Expense History")
if st.session_state.food_expenses:
    df = pd.DataFrame(st.session_state.food_expenses)
    df = df.drop(columns=["id", "user_id"], errors="ignore")
    st.dataframe(df)

    # ---------- Budget Alerts ----------
    st.header("🚨 Budget Alerts")
    grouped = df.groupby("place")["amount"].sum().reset_index()
    for _, row in grouped.iterrows():
        place = row["place"]
        spent = row["amount"]
        budget = st.session_state.food_budgets.get(place)
        if budget and spent > budget:
            st.warning(f"⚠️ Overspent at {place} by ₹{int(spent - budget)}")

    # ---------- Dashboard ----------
    st.header("📊 Insight Corner")
    grouped["percentage"] = (grouped["amount"] / grouped["amount"].sum() * 100).round(2)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Spending by Place")
        bar = alt.Chart(grouped).mark_bar().encode(
            x="place", y="amount", tooltip=["place", "amount"]
        ).properties(width=400, height=300)
        st.altair_chart(bar)

    with col2:
        st.subheader("Spending Distribution")
        pie = alt.Chart(grouped).mark_arc().encode(
            theta="amount", color="place", tooltip=["place", "amount", "percentage"]
        ).properties(width=400, height=300)
        st.altair_chart(pie)

    # ---------- Summary ----------
    st.header("📌 Summary")
    st.success(f"Total Spent: ₹{int(df['amount'].sum())}")

# ---------- Clear Data ----------
st.header("🧹 Clear All Data")
if st.button("Clear & Download Report"):
    df = pd.DataFrame(st.session_state.food_expenses)
    df = df.drop(columns=["id", "user_id"], errors="ignore")
    if not df.empty:
        grouped = df.groupby("place")["amount"].sum().reset_index()
        for _, row in grouped.iterrows():
            place = row["place"]
            spent = row["amount"]
            budget = st.session_state.food_budgets.get(place)
            if budget and spent > budget:
                st.warning(f"⚠️ Overspent at {place} by ₹{int(spent - budget)}")

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Report", csv, file_name="expense_report.csv", mime="text/csv")

    uid = get_user_id()
    supabase.table("expenses").delete().eq("user_id", uid).execute()
    supabase.table("budgets").delete().eq("user_id", uid).execute()
    st.session_state.food_expenses = []
    st.session_state.food_budgets = {}
    st.success("✅ All data cleared.")
