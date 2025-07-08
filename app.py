import streamlit as st
import pandas as pd
import datetime
import altair as alt
from supabase import create_client, Client

# ------------------------ Supabase Config ------------------------
SUPABASE_URL = "https://cwyvjesaxmcidlsceigj.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY"  # Replace with your actual key

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------------ Helper Function ------------------------
def get_user_id():
    user = st.session_state.get("user")
    return user.id if user else None

# ------------------------ Login & Signup ------------------------
if "user" not in st.session_state:
    st.title("Welcome to Campus Food Expense Tracker!")
    auth_mode = st.radio("Choose Action", ["Login", "Sign Up"])
    email = st.text_input("Enter your E-mail")
    password = st.text_input("Enter your Password", type="password")

    if st.button(auth_mode):
        if len(password) < 6:
            st.error("Password must be at least 6 characters long")
        else:
            try:
                if auth_mode == "Sign Up":
                    res = supabase.auth.sign_up({"email": email, "password": password})
                    st.success("Account created! Please verify your email before logging in.")
                else:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    if hasattr(res, "user") and res.user:
                        st.session_state.user = res.user
                        uid = res.user.id

                        # Load budgets
                        res_budgets = supabase.table("budgets").select("*").eq("user_id", uid).execute()
                        st.session_state.food_budgets = {row["place"]: row["amount"] for row in res_budgets.data} if res_budgets.data else {}

                        # Load expenses
                        res_expenses = supabase.table("expenses").select("*").eq("user_id", uid).execute()
                        st.session_state.food_expenses = res_expenses.data if res_expenses.data else []

                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("Login failed. Please check your credentials.")
            except Exception:
                st.error("Something went wrong. Try again.")

    st.stop()

# ------------------------ Sidebar Navigation ------------------------
st.sidebar.title("Menu")
page = st.sidebar.radio("Go to", ["Welcome", "Add Budgets", "Add Expenses", "Dashboard", "Budget Alerts", "Logout"])

user_id = get_user_id()
food_places = ['Amul', 'Just Chill', 'Tapri', 'Dawat', 'GoInsta', '2D', 'TeaPost', 'South Point',
               'Atul Bakery', 'Krupa General', 'Hunger Games', 'Mahavir', 'Outside Restaurant Visit', 'Online food delivery']

# ------------------------ Page: Logout ------------------------
if page == "Logout":
    st.session_state.clear()
    st.success("Logged out successfully!")
    st.rerun()

# ------------------------ Page: Welcome ------------------------
elif page == "Welcome":
    st.title("Welcome to the Campus Food Expense Tracker!")
    st.markdown('''
    This app helps you:
    - 🧾 Track your food spending across campus stalls  
    - 💸 Set and monitor weekly budgets  
    - 📊 Visualize your spending habits  

    Use the sidebar to get started!
    ''')

# ------------------------ Page: Add Budgets ------------------------
elif page == "Add Budgets":
    st.header("Set Your Weekly Budgets!")
    for place in food_places:
        budget = st.number_input(f"{place} Budget", min_value=0, step=50, value=st.session_state.get("food_budgets", {}).get(place, 0), key=f"budget_{place}")

        if budget > 0:
            existing = supabase.table("budgets").select("*").eq("user_id", user_id).eq("place", place).execute()
            if existing.data:
                supabase.table("budgets").update({"amount": budget}).eq("id", existing.data[0]["id"]).execute()
            else:
                supabase.table("budgets").insert({"user_id": user_id, "place": place, "amount": budget}).execute()

            st.session_state.food_budgets[place] = budget

# ------------------------ Page: Add Expenses ------------------------
elif page == "Add Expenses":
    st.header("Add Food Expense")
    with st.form("food_expense_form"):
        place = st.selectbox("Select Food Place", food_places)
        amount = st.slider("Amount Spent", min_value=10, max_value=1000, step=10)
        note = st.text_input("Optional Note")
        date_input = st.date_input("Date of Expense", value=datetime.date.today())
        time_input = st.time_input("Time of Expense", value=datetime.datetime.now().time())

        full_timestamp = datetime.datetime.combine(date_input, time_input).strftime("%d-%m-%Y %H:%M:%S")

        submit = st.form_submit_button("Add Expense")

        if submit:
            supabase.table("expenses").insert({
                "user_id": user_id,
                "timestamp": full_timestamp,
                "place": place,
                "note": note,
                "amount": amount
            }).execute()

            # Also update session state
            st.session_state.food_expenses.append({
                "user_id": user_id,
                "timestamp": full_timestamp,
                "place": place,
                "note": note,
                "amount": amount
            })

            st.success(f"Added ₹{amount} at {place} on {full_timestamp}")
            st.rerun()

# ------------------------ Page: Budget Alerts ------------------------
elif page == "Budget Alerts":
    st.header("🚨 Budget Alerts")
    if st.session_state.get("food_expenses"):
        df = pd.DataFrame(st.session_state.food_expenses)
        df_grouped = df.groupby("place")["amount"].sum().reset_index()
        for _, row in df_grouped.iterrows():
            place = row["place"]
            spent = row["amount"]
            budget = st.session_state.food_budgets.get(place)
            if budget and spent > budget:
                st.warning(f"Overspent at **{place}** by ₹{int(spent - budget)}")
    else:
        st.info("No expenses yet to analyze.")

# ------------------------ Page: Dashboard ------------------------
elif page == "Dashboard":
    st.header("📊 Insight Dashboard")
    if st.session_state.get("food_expenses"):
        df = pd.DataFrame(st.session_state.food_expenses)
        df_grouped = df.groupby("place")["amount"].sum().reset_index()
        df_grouped["Percentage"] = (df_grouped["amount"] / df_grouped["amount"].sum() * 100).round(2)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Spending by Place")
            bar_chart = alt.Chart(df_grouped).mark_bar().encode(
                x=alt.X("place", sort="-y"),
                y="amount",
                color=alt.Color("place", scale=alt.Scale(scheme="tableau20")),
                tooltip=["place", "amount"]
            ).properties(width=400, height=300)
            st.altair_chart(bar_chart)

        with col2:
            st.subheader("Spending Distribution")
            pie_chart = alt.Chart(df_grouped).mark_arc().encode(
                theta="amount",
                color=alt.Color("place", scale=alt.Scale(scheme="pastel1")),
                tooltip=["place", "amount", "Percentage"]
            ).properties(width=400, height=300)
            st.altair_chart(pie_chart)

        st.subheader("💰 Summary")
        total_spent = df["amount"].sum()
        st.success(f"Total amount spent: ₹{int(total_spent)}")

    else:
        st.info("No expenses to visualize yet.")
