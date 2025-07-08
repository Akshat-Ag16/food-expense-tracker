import streamlit as st
import pandas as pd
import datetime
import altair as alt

from supabase import create_client, Client
SUPABASE_URL = "https://cwyvjesaxmcidlsceigj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN3eXZqZXNheG1jaWRsc2NlaWdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE3MjU3NjUsImV4cCI6MjA2NzMwMTc2NX0.dlKjz0NEY-EHo2au01wpwa6OPb48ly8swrJ7WqHo5Hg"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user_id():
    user = st.session_state.get("user")
    if user:
        return user.id
    return None

if "user" not in st.session_state:
    st.title("Welcome to Campus Food Expense Tracker!")
    auth_mode = st.radio("Choose Action", ["Login", "Sign Up"])
    email = st.text_input("Enter your E-mail")
    password = st.text_input("Enter your password", type="password")

    if st.button(auth_mode):
        if len(password) < 6:
            st.error("Password must be atleast 6 characters long")
        else:
            try:
                if auth_mode == "Sign Up":
                    res = supabase.auth.sign_up({"email": email, "password": password})
                    st.success("Account created! Please check your email and verify before logging in")
                else:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    if res.user:
                        st.session_state.user = res.user
                        st.success("Logged in Successfully!")
                        if get_user_id():
                            res_budgets = supabase.table("budgets").select("*").eq("user_id", get_user_id()).execute()
                            st.session_state.food_budgets = {
                            row["place"]: row["amount"] for row in res_budgets.data
                            } if res_budgets.data else {}
                            res_expenses = supabase.table("expenses").select("*").eq("user_id", get_user_id()).execute()
                            st.session_state.food_expenses = res_expenses.data if res_expenses.data else []
                        st.rerun()
                    else:
                        st.error("Login failed! Try again")
            except Exception:
                st.error("Something went wrong. Please check your details and try again!")
    st.stop()

st.sidebar.title("Menu")
page = st.sidebar.radio("Go to", ["Welcome", "Add Budgets", "Add Expenses", "Dashboard","Budget Alerts", "Logout"])

user_id = get_user_id()

if page == "Logout":
    st.session_state.clear()
    st.success("Logged out sucessfully!")
    st.rerun()

elif page == "Welcome":
    st.title("Welcome to the Campus Food Expense Tracker!")
    st.markdown('''
    This app helps you:
    - Track your food spending across campus stalls  
    - Set and monitor weekly budgets  
    - Visualize your spending habits  

    Use the sidebar to get started! 
    ''')

elif page == "Add Budgets":
    st.header("Set your weekly budgets!")
    food_places = ['Amul','Just Chill', 'Tapri', 'Dawat', 'GoInsta', '2D', 'TeaPost', 'South Point', 'Atul Bakery', 'Krupa General', 'Hunger Games', 'Mahavir', 'Outside Restaurant Visit', 'Online food delivery']

    for place in food_places:
        budget = st.sidebar.number_input(f"{place} Budget", min_value = 0, step=50, value = 0, key= f"budget_{place}")

        if budget > 0 and get_user_id():
            existing = supabase.table("budgets").select("*").eq("user_id", get_user_id()).eq("place", place).execute()

            if existing.data:
                supabase.table("budgets").update({"amount": budget}).eq("id", existing.data[0]["id"]).execute() 
            else:
                supabase.table("budgets").insert({"user_id": get_user_id(), "place": place, "amount": budget}).execute()
            st.session_state.food_budgets[place] = budget

elif page == "Add Expense":
    st.header("Add food expense!")
    food_places = ['Amul','Just Chill', 'Tapri', 'Dawat', 'GoInsta', '2D', 'TeaPost', 'South Point', 'Atul Bakery', 'Krupa General', 'Hunger Games', 'Mahavir', 'Outside Restaurant Visit', 'Online food delivery']
    with st.form("food_expense_form"):
        place = st.selectbox("Select Food Place", food_places)
        amount = st.slider("Amount Spent", min_value = 10, value = 10, step=10, max_value=1000)
        note = st.text_input("Optional Note")

        date_input = st.date_input("Date of Expense", value=datetime.date.today())
        time_input = st.time_input("Time of Expense", value=datetime.time(12, 0))

        full_timestamp = datetime.datetime.combine(date_input, time_input).strftime("%d-%m-%Y %H:%M:%S")

        submit = st.form_submit_button("Add expense!")

        if submit and get_user_id():
            supabase.table("expenses").insert({
                "user_id": get_user_id(),
                "timestamp": full_timestamp,
                "place": place,
                "note": note,
                "amount": amount
            }).execute()

            st.success(f"Added {amount} at {place} on {full_timestamp}")
            st.rerun()

elif page == "Budget Alerts":
    st.header("🚨 Budget Alerts")
    if st.session_state.food_expenses:
        df = pd.DataFrame(st.session_state.food_expenses)
        df_grouped = df.groupby("Place")["Amount"].sum().reset_index()
        for _, row in df_grouped.iterrows():
            place = row["Place"]
            spent = row["Amount"]
            budget = st.session_state.food_budgets.get(place)
            if budget and spent > budget:
                st.warning(f"Overspent at **{place}** by ₹{int(spent - budget)}")
    else:
        st.info("No expenses added yet!")

elif page == "Dashboard":
        st.header("Insight Corner!")

if "food_expenses" in st.session_state and st.session_state.food_expenses:
    df = pd.DataFrame(st.session_state.food_expenses)
    df_grouped = df.groupby("Place")["Amount"].sum().reset_index()
    df_grouped["Percentage"] = (df_grouped["Amount"] / df_grouped["Amount"].sum() * 100).round(2)

    col1,col2 = st.columns(2)

    with col1:
        st.subheader("Spending by Place")
        bar_chart = alt.Chart(df_grouped).mark_bar().encode(
            x=alt.X("Place"),
            y="Amount",
            color=alt.Color("Place", scale=alt.Scale(scheme="tableau20")),
            tooltip = ['Place','Amount']
        ).properties(width = 400, height = 300)
        st.altair_chart(bar_chart)

    with col2:
        st.subheader("Spending Distribution")
        pie_chart = alt.Chart(df_grouped).mark_arc().encode(
            theta="Amount",
            color=alt.Color("Place", scale=alt.Scale(scheme="pastel1")),
            tooltip=["Place", "Amount", "Percentage"]
        ).properties(width=400, height=300)
        st.altair_chart(pie_chart)

    st.header("Summary")
    total_spent = df["Amount"].sum()
    st.success(f"Total amount spent is {int(total_spent)}")
else:
    st.header("Summary")
    st.info("Nothing to summarize")