💰 FinTrack – Expense Tracker

FinTrack is a Streamlit-based personal expense tracker that helps users record, manage, and analyze their spending with budgets, interactive dashboards, and CSV-based storage.

Features:

🔐 Secure login/signup with password hashing

📝 Add single or bulk expenses via CSV

📊 Dashboard: category-wise spending, monthly trends, day-wise analysis

💸 Set & track category budgets with alerts

🔍 Filter expenses by date, category, and amount

📤 Export all or filtered expenses as CSV

🗂 Add custom categories

Tech Stack:

Python | Streamlit | Pandas | Matplotlib | CSV storage

Project Structure:
expense-tracker/
│── app.py
│── requirements.txt
│── README.md
│── sample_users.csv
│── sample_expenses.csv
│── sample_categories.csv
│── sample_budgets.csv
│── .gitignore


⚠️ Real user data files (*.csv, *.db) are excluded for security.

How to Run:
git clone https://github.com/Parshva-Vasani/expense-trackor.git
cd expense-trackor
pip install -r requirements.txt
streamlit run app.py
