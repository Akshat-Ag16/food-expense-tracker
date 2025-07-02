import streamlit as st
import pandas as pd
import datetime
import altair as alt

if "food_budgets" not in st.session_state:
    st.session_state.food_budgets = []

st.set_page_config(page_title="Food Expense Tracker", layout="wide")
st.title("Your weekly food expense tracker at IITGN")

food_places = ['Amul','Just Chill', 'Dawat', 'GoInsta', '2D', 'TeaPost', 'South Point', 'Atul Bakery', 'Krupa General', 'Hunger Games', 'Mahavir', 'Outside Restaurant Visit', 'Online food delivery']

st.sidebar.header("Set your weekly budgets")

for place in food_places:
    budget = st.sidebar.number_input(f"{place} Budget", min_value = 0, step=50, value = 0, key= f"budget_{place}")
    if budget > 0:
        st.session_state.food_budgets['place'] = budget

st.header("Add food expense!")

with st.form("food_expense_form"):
    place = st.selectbox("Select Food Place", food_places)
    amount = st.slider("Amount Spent", min_value = 1, value = 10, step=10)
    note = st.text_input("Optional Note")

    date_input = st.date_input("Date of Expense", value=datetime.date.today())
    time_input = st.time_input("Time of Expense", value=datetime.datetime.now().time())

    full_timestamp = datetime.datetime.combine(date_input, time_input).strftime("%d-%m-%Y %H:%M:%S")

    submit = st.form_submit_button("Add expense!")

    if submit:
        new_entry = {
            "Timestamp": full_timestamp,
            "Place": place,
            "Note": note,
            "Amount": amount
        }

        if "food_expenses" not in st.session_state:
            st.session_state.food_expenses = []

        st.session_state.food_expenses.append(new_entry)
        st.success(f"Added {amount} in {place} on {full_timestamp}")

st.header("Expense History")

if "food expenses" in st.session_state and st.session_state.food_expenses:
    df = pd.DataFrame(st.session_state.food_expenses)
    st.dataframe(df)

    st.header("Budget Alerts!")

    df_grouped = df.groupby("Place")["Amount"].sum().reset_index()

    for _,row in df_grouped.iterrows():
        place = row["Place"]
        spent = row["Amount"]
        budget = st.session_state.food_budgets.get(place)

        if budget and spent > budget:
            st.warning(f"Overspent at {place} by {int({budget}-{spent})}")

    st.header("Insight Corner!")

    col1,col2 = st.columns(2)

    with col1:
        st.subheader("Spending by Place")
        bar_chart = alt.Chart(df_grouped).mark_bar().encode(
            x=alt.X("Place"),
            y="Amount",
            tooltip = ['Place','Amount']
        ).properties(width = 400, height = 300)
        st.altair_chart(bar_chart)

    with col2:
        st.subheader("Spending Distribution")
        pie_chart = alt.Chart(df_grouped).mark_arc().encode(
            theta = "Amount",
            color = "Place",
            tooltip = ["Place", "Amount"]
        ).properties(width = 400, height = 300)
        st.altair_chart(pie_chart)

        st.header("Summary")
        total_spent = df["Amount"].sum()
        st.success(f"Total amount spent is {int(total_spent)}")
else:
    st.info("No expenses added yet!")