from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------- Basic setup ----------
st.set_page_config(page_title="Student Expense Tracker", page_icon="💸", layout="centered")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "expenses.csv"

CATEGORIES = ["Food", "Rent", "Transport", "Groceries", "Entertainment", "Shopping", "Health", "Other"]


# ---------- Helper functions ----------
def load_expenses(path: Path) -> pd.DataFrame:
    """Load expenses from CSV. If file doesn't exist, return an empty DataFrame."""
    if not path.exists():
        return pd.DataFrame(columns=["date", "category", "amount", "note"])

    df = pd.read_csv(path)
    # Clean types
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["category"] = df["category"].astype(str)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["note"] = df["note"].fillna("").astype(str)

    # Remove broken rows (if any)
    df = df.dropna(subset=["date", "amount"]).copy()
    return df


def save_expenses(df: pd.DataFrame, path: Path) -> None:
    """Save expenses to CSV."""
    df_to_save = df.copy()
    df_to_save["date"] = df_to_save["date"].astype(str)  # CSV stores as text
    df_to_save.to_csv(path, index=False)


def add_expense(df: pd.DataFrame, expense_date: date, category: str, amount: float, note: str) -> pd.DataFrame:
    """Add one new expense row and return updated DataFrame."""
    new_row = pd.DataFrame(
        [{
            "date": expense_date,
            "category": category,
            "amount": float(amount),
            "note": note.strip()
        }]
    )
    out = pd.concat([df, new_row], ignore_index=True)
    return out


# ---------- Load existing data ----------
df = load_expenses(CSV_PATH)

# ---------- UI ----------
st.title("💸 Student Expense Tracker")
st.caption("Add expenses, store them in a CSV, and see quick summaries.")

st.divider()

st.subheader("➕ Add a new expense")

with st.form("add_expense_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        expense_date = st.date_input("Date", value=date.today())
    with col2:
        category = st.selectbox("Category", CATEGORIES)

    amount = st.number_input("Amount ($)", min_value=0.0, value=0.0, step=1.0)
    note = st.text_input("Note (optional)", placeholder="e.g., lunch, Uber, rent split")

    submitted = st.form_submit_button("Add Expense")

if submitted:
    if amount <= 0:
        st.error("Amount must be greater than 0.")
    else:
        df = add_expense(df, expense_date, category, amount, note)
        save_expenses(df, CSV_PATH)
        st.success("Expense added ✅")

st.divider()

st.subheader("📋 Your expenses")

if df.empty:
    st.info("No expenses yet. Add your first one above.")
else:
    # Sort newest first
    df_display = df.sort_values(by="date", ascending=False).reset_index(drop=True)

    # Quick filters
    colA, colB = st.columns(2)
    with colA:
        selected_category = st.selectbox("Filter by category", ["All"] + CATEGORIES)
    with colB:
        search_note = st.text_input("Search in notes", placeholder="type keyword...")

    filtered = df_display.copy()
    if selected_category != "All":
        filtered = filtered[filtered["category"] == selected_category]
    if search_note.strip():
        filtered = filtered[filtered["note"].str.lower().str.contains(search_note.strip().lower(), na=False)]

    st.dataframe(filtered, use_container_width=True)

    st.divider()
    st.subheader("📊 Summary")

    total_spent = df["amount"].sum()
    st.metric("Total spent", f"${total_spent:,.2f}")

    by_category = df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    st.write("Spend by category:")
    st.dataframe(by_category, use_container_width=True)

    # Streamlit built-in chart (simple + fast)
    st.bar_chart(by_category.set_index("category")["amount"])

    st.divider()
    st.subheader("🧹 Manage")

    colX, colY = st.columns(2)
    with colX:
        if st.button("Download CSV"):
            st.download_button(
                label="Click to download expenses.csv",
                data=CSV_PATH.read_bytes(),
                file_name="expenses.csv",
                mime="text/csv",
            )

    with colY:
        if st.button("Clear ALL data"):
            # Safety: require a second confirmation
            st.warning("Click again to confirm deletion.")
            if "confirm_clear" not in st.session_state:
                st.session_state["confirm_clear"] = True
            else:
                CSV_PATH.unlink(missing_ok=True)
                st.session_state.pop("confirm_clear", None)
                st.success("All data cleared. Refreshing...")
                st.experimental_rerun()

