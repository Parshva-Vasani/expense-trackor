import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os
import hashlib
from dateutil.relativedelta import relativedelta

# File paths for data storage
USERS_FILE = 'users.csv'
EXPENSES_FILE = 'expenses.csv'
CATEGORIES_FILE = 'categories.csv'
BUDGETS_FILE = 'budgets.csv'

# Initialize CSV files if they don’t exist
for file in [USERS_FILE, EXPENSES_FILE, CATEGORIES_FILE, BUDGETS_FILE]:
    if not os.path.exists(file):
        pd.DataFrame().to_csv(file, index=False)

# Set Streamlit page configuration
st.set_page_config(page_title="FinTrack", page_icon="💰", layout="centered")

### Authentication Functions
def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    """Create a new user with a hashed password."""
    if not username or not password:
        return False
    users = pd.read_csv(USERS_FILE)
    if username in users['username'].values:
        return False
    users = pd.concat([users, pd.DataFrame([{
        'username': username,
        'password': hash_password(password)
    }])], ignore_index=True)
    users.to_csv(USERS_FILE, index=False)
    return True

def verify_user(username, password):
    """Verify user credentials."""
    users = pd.read_csv(USERS_FILE)
    user = users[users['username'] == username]
    return not user.empty and user.iloc[0]['password'] == hash_password(password)

def auth_page():
    """Display login and signup page."""
    st.title("🔒 FinTrack Login")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if verify_user(username, password):
                    st.session_state.user = username
                    st.rerun()
                else:
                    st.error("Invalid credentials")

    with tab2:
        with st.form("signup"):
            new_user = st.text_input("New Username")
            new_pass = st.text_input("New Password", type="password")
            if st.form_submit_button("Create Account"):
                if create_user(new_user, new_pass):
                    st.success("Account created! Please login")
                else:
                    st.error("Invalid input or username exists")

### Expense Tracker Class
class ExpenseTracker:
    def __init__(self, username):
        self.username = username
        self.load_data()

    def load_data(self):
        """Load user-specific data from CSV files."""
        self.expenses = pd.read_csv(EXPENSES_FILE)
        self.expenses = self.expenses[self.expenses['username'] == self.username]
        if not self.expenses.empty:
            self.expenses['date'] = pd.to_datetime(self.expenses['date'])

        self.categories = pd.read_csv(CATEGORIES_FILE)
        self.categories = self.categories[self.categories['username'] == self.username]

        self.budgets = pd.read_csv(BUDGETS_FILE)
        self.budgets = self.budgets[self.budgets['username'] == self.username]

    def get_available_categories(self):
        """Return all available categories (default + user-added)."""
        default_cats = ["Food", "Transport", "Housing", "Other"]
        user_cats = self.categories['category'].tolist()
        return list(set(default_cats + user_cats))

    def add_expense(self, expense_data):
        """Add an expense, checking against budget limits."""
        category = expense_data['category']
        amount = expense_data['amount']

        # Validate category
        if category not in self.get_available_categories():
            return False, "Category does not exist."

        # Check budget limit
        budget_row = self.budgets[self.budgets['category'] == category]
        if not budget_row.empty:
            budget = budget_row.iloc[0]['amount']
            current_total = self.expenses[self.expenses['category'] == category]['amount'].sum()
            if current_total + amount > budget:
                return False, "Adding this expense would exceed your budget for this category."

        # Add expense
        expenses = pd.read_csv(EXPENSES_FILE)
        expense_data['date'] = expense_data['date'].strftime('%Y-%m-%d')
        expenses = pd.concat([expenses, pd.DataFrame([expense_data])], ignore_index=True)
        expenses.to_csv(EXPENSES_FILE, index=False)
        self.load_data()
        return True, "Expense added successfully."

    def add_bulk_expenses(self, uploaded_file):
        """Add multiple expenses from a CSV file."""
        try:
            df = pd.read_csv(uploaded_file)
            required_cols = {'date', 'category', 'amount', 'description'}
            if not required_cols.issubset(df.columns):
                return False, "CSV must contain date, category, amount, description columns."

            df['username'] = self.username
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            if df['date'].isnull().any():
                return False, "Invalid date format in CSV. Use YYYY-MM-DD."

            errors = []
            for _, row in df.iterrows():
                success, message = self.add_expense(row.to_dict())
                if not success:
                    errors.append(f"Row with {row['description']}: {message}")

            if errors:
                return False, "\n".join(errors)
            return True, "All expenses added successfully."
        except Exception as e:
            return False, f"Error processing file: {str(e)}"

    def add_category(self, category):
        """Add a new category, ensuring no duplicates."""
        default_cats = ["Food", "Transport", "Housing", "Other"]
        if not category or category in default_cats or category in self.categories['category'].tolist():
            return False
        cats = pd.read_csv(CATEGORIES_FILE)
        cats = pd.concat([cats, pd.DataFrame([{
            'username': self.username,
            'category': category
        }])], ignore_index=True)
        cats.to_csv(CATEGORIES_FILE, index=False)
        self.load_data()
        return True

    def set_budget(self, category, amount):
        """Set or update a budget for a category."""
        budgets = pd.read_csv(BUDGETS_FILE)
        budgets = budgets[~((budgets['username'] == self.username) & (budgets['category'] == category))]
        new_budget = pd.DataFrame([{
            'username': self.username,
            'category': category,
            'amount': amount
        }])
        budgets = pd.concat([budgets, new_budget], ignore_index=True)
        budgets.to_csv(BUDGETS_FILE, index=False)
        self.load_data()

    def remove_budget(self, category):
        """Remove the budget for a specific category."""
        budgets = pd.read_csv(BUDGETS_FILE)
        budgets = budgets[~((budgets['username'] == self.username) & (budgets['category'] == category))]
        budgets.to_csv(BUDGETS_FILE, index=False)
        self.load_data()

    def get_filtered_expenses(self, start_date, end_date, categories=None, min_amount=None, max_amount=None):
        """Filter expenses based on criteria."""
        if self.expenses.empty:
            return pd.DataFrame()

        mask = (self.expenses['date'] >= pd.to_datetime(start_date)) & \
               (self.expenses['date'] <= pd.to_datetime(end_date))

        if categories:
            mask &= self.expenses['category'].isin(categories)
        if min_amount is not None:
            mask &= self.expenses['amount'] >= min_amount
        if max_amount is not None:
            mask &= self.expenses['amount'] <= max_amount

        return self.expenses[mask].copy()

### Main Application
def main_app():
    tracker = ExpenseTracker(st.session_state.user)
    st.title(f"💰 FinTrack - Welcome {st.session_state.user}")

    tabs = st.tabs(["📝 Add", "📊 Dashboard", "⚙️ Manage", "📤 Export"])

    #### Add Tab
    with tabs[0]:
        st.subheader("Add Single Expense")
        with st.form("expense_form"):
            col1, col2, col3 = st.columns([2, 2, 1])
            date = col1.date_input("Date", datetime.today())
            category = col2.selectbox("Category", tracker.get_available_categories())
            amount = col3.number_input("Amount", min_value=0.0, format="%.2f")
            description = st.text_input("Description")
            if st.form_submit_button("Add Expense"):
                success, message = tracker.add_expense({
                    'username': st.session_state.user,
                    'date': date,
                    'category': category,
                    'amount': amount,
                    'description': description
                })
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        st.subheader("Bulk Upload Expenses")
        uploaded_file = st.file_uploader("Upload CSV (date, category, amount, description)", type="csv")
        if uploaded_file:
            success, message = tracker.add_bulk_expenses(uploaded_file)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    #### Dashboard Tab
    with tabs[1]:
        with st.expander("🔍 Filters", expanded=True):
            col1, col2 = st.columns(2)
            start_date = col1.date_input("Start", value=tracker.expenses['date'].min() if not tracker.expenses.empty else datetime.today())
            end_date = col2.date_input("End", value=tracker.expenses['date'].max() if not tracker.expenses.empty else datetime.today())
            col3, col4 = st.columns(2)
            categories = col3.multiselect("Categories", options=tracker.get_available_categories())
            amount_range = col4.slider("Amount Range",
                                       min_value=0,
                                       max_value=int(tracker.expenses['amount'].max()) if not tracker.expenses.empty else 10000,
                                       value=(0, int(tracker.expenses['amount'].max()) if not tracker.expenses.empty else 10000))

        filtered_expenses = tracker.get_filtered_expenses(start_date, end_date, categories, amount_range[0], amount_range[1])

        if not filtered_expenses.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Spent", f"₹{filtered_expenses['amount'].sum():.2f}")
            col2.metric("Average per Day", f"₹{filtered_expenses.groupby('date')['amount'].sum().mean():.2f}")
            col3.metric("Most Spent On", filtered_expenses.groupby('category')['amount'].sum().idxmax())

            st.subheader("Budget Status")
            for _, budget in tracker.budgets.iterrows():
                spent = filtered_expenses[filtered_expenses['category'] == budget['category']]['amount'].sum()
                percent = min((spent / budget['amount'] * 100) if budget['amount'] > 0 else 0, 100)
                st.write(f"{budget['category']}")
                col1, col2 = st.columns([3, 1])
                col1.progress(percent / 100)
                col2.write(f"{percent:.1f}%")
                st.write(f"₹{spent:.2f} / ₹{budget['amount']:.2f}")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Category Distribution")
                categories_sum = filtered_expenses.groupby('category')['amount'].sum()
                plt.figure(figsize=(6, 6))
                plt.pie(categories_sum, labels=categories_sum.index, autopct='%1.1f%%', startangle=140)
                plt.title("Category Distribution")
                st.pyplot(plt)
                plt.clf()  # Clear the figure to prevent overlap

            with col2:
                st.subheader("Spending Trend")
                monthly = filtered_expenses.groupby(filtered_expenses['date'].dt.to_period('M'))['amount'].sum()
                plt.figure(figsize=(10, 4))
                plt.plot(monthly.index.astype(str), monthly.values, marker='o')
                plt.xlabel("Month")
                plt.ylabel("Amount")
                plt.title("Spending Trend")
                plt.xticks(rotation=45)
                st.pyplot(plt)
                plt.clf()  # Clear the figure

            st.subheader("Recent Expenses")
            recent = filtered_expenses.sort_values('date', ascending=False).head(5).copy()
            recent['date'] = recent['date'].dt.strftime('%Y-%m-%d')
            st.table(recent[['date', 'category', 'amount', 'description']])

            st.subheader("Spending by Day of Week")
            filtered_expenses['day_of_week'] = filtered_expenses['date'].dt.day_name()
            day_spending = filtered_expenses.groupby('day_of_week')['amount'].sum().reindex(
                ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            )
            plt.figure(figsize=(8, 4))
            plt.bar(day_spending.index, day_spending.values)
            plt.xlabel("Day")
            plt.ylabel("Total Spent")
            plt.title("Spending by Day of Week")
            plt.xticks(rotation=45)
            st.pyplot(plt)
            plt.clf()  # Clear the figure

            st.subheader("Expense Notes Summary")
            top_expenses = filtered_expenses.sort_values('amount', ascending=False).head(5)
            for _, exp in top_expenses.iterrows():
                st.write(f"₹{exp['amount']:.2f} on {exp['date'].strftime('%Y-%m-%d')} ({exp['category']}): {exp['description']}")

        else:
            st.info("No expenses found for the selected filters")

        st.subheader("This Month vs. Last Month")
        today = datetime.today()
        current_month_start = today.replace(day=1)
        previous_month_start = current_month_start - relativedelta(months=1)
        last_month_expenses = tracker.expenses[(tracker.expenses['date'] >= previous_month_start) & (tracker.expenses['date'] < current_month_start)]
        this_month_expenses = tracker.expenses[tracker.expenses['date'] >= current_month_start]
        last_month_total = last_month_expenses['amount'].sum()
        this_month_total = this_month_expenses['amount'].sum()
        col1, col2 = st.columns(2)
        col1.metric("Last Month", f"₹{last_month_total:.2f}")
        col2.metric("This Month", f"₹{this_month_total:.2f}")

    #### Manage Tab
    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Categories")
            st.write("Available Categories:")
            for cat in tracker.get_available_categories():
                st.write(cat)
            with st.form("category_form"):
                new_cat = st.text_input("New Category")
                if st.form_submit_button("Add"):
                    if tracker.add_category(new_cat):
                        st.success("Category added")
                        st.rerun()
                    else:
                        st.error("Invalid category or already exists")
            st.subheader("Category Usage")
            if not tracker.expenses.empty:
                usage = tracker.expenses.groupby('category').agg(count=('amount', 'size'), total=('amount', 'sum'))
                st.table(usage)
            else:
                st.write("No expenses to analyze.")

        with col2:
            st.subheader("Budgets")
            st.write("Current Budgets:")
            if not tracker.budgets.empty:
                for _, budget in tracker.budgets.iterrows():
                    st.write(f"{budget['category']}: ₹{budget['amount']:.2f}")
            else:
                st.write("No budgets set.")
            with st.form("budget_form"):
                cat = st.selectbox("Select Category", tracker.get_available_categories())
                amt = st.number_input("Budget Amount", min_value=0.0, step=0.01, format="%.2f")
                if st.form_submit_button("Set Budget"):
                    tracker.set_budget(cat, amt)
                    st.success("Budget updated")
                    st.rerun()
            if not tracker.budgets.empty:
                with st.form("remove_budget_form"):
                    category_to_remove = st.selectbox("Select Category to Remove Budget", tracker.budgets['category'].tolist())
                    if st.form_submit_button("Remove Budget"):
                        tracker.remove_budget(category_to_remove)
                        st.success(f"Budget for {category_to_remove} removed")
                        st.rerun()
            st.subheader("Budget Alerts")
            alert_enabled = st.checkbox("Enable Budget Alerts", value=False)
            if alert_enabled:
                threshold = st.slider("Alert Threshold (%)", 0, 100, 80)
                if not tracker.budgets.empty and not tracker.expenses.empty:
                    for _, budget in tracker.budgets.iterrows():
                        spent = tracker.expenses[tracker.expenses['category'] == budget['category']]['amount'].sum()
                        percent = (spent / budget['amount'] * 100) if budget['amount'] > 0 else 0
                        if percent >= threshold:
                            st.warning(f"Alert: {budget['category']} spending at {percent:.1f}% of ₹{budget['amount']:.2f}")

    #### Export Tab
    with tabs[3]:
        if not tracker.expenses.empty:
            st.subheader("Export All Expenses")
            st.download_button("Download All Expenses",
                              data=tracker.expenses.to_csv(index=False),
                              file_name="all_expenses.csv",
                              mime="text/csv")
            st.subheader("Export Filtered Expenses")
            if not filtered_expenses.empty:
                st.download_button("Download Filtered Expenses",
                                  data=filtered_expenses.to_csv(index=False),
                                  file_name="filtered_expenses.csv",
                                  mime="text/csv")
            else:
                st.info("No filtered expenses to export.")
        else:
            st.info("No expenses to export.")
        if not tracker.budgets.empty:
            st.subheader("Export Budgets")
            st.download_button("Download Budgets",
                              data=tracker.budgets.to_csv(index=False),
                              file_name="budgets.csv",
                              mime="text/csv")
        else:
            st.info("No budgets to export.")

### Entry Point
if __name__ == "__main__":
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        auth_page()
    else:
        main_app()