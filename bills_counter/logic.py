import pandas as pd
import random
from datetime import datetime
import os

def load_accounts(path):
    """Load accounts from CSV or Excel and rename 'Account_No' to 'account_number'."""
    if path.endswith(".xlsx"):
        df = pd.read_excel(path, engine="openpyxl")
    elif path.endswith(".csv"):
        df = pd.read_csv(path)
    else:
        raise ValueError("Unsupported file format. Please use .csv or .xlsx")

    if "Account_No" in df.columns:
        df.rename(columns={"Account_No": "account_number"}, inplace=True)

    # ✅ Automatically detect user types from SUBTYPE column
    if "SUBTYPE" in df.columns:
        user_types = df["SUBTYPE"].dropna().unique().tolist()
        print("Detected user types:", user_types)
    else:
        print("Warning: 'SUBTYPE' column not found in input file.")

    return df.to_dict(orient="records")

def generate_bill(account):
    """Generate bill details from an account dictionary."""
    account_no = account.get("account_number")

    if pd.isnull(account_no) or not str(account_no).isdigit():
        raise ValueError("Invalid or missing account number.")

    consumption = round(random.uniform(100, 1500), 2)
    rate = round(random.uniform(0.1, 0.3), 2)
    total = round(consumption * rate, 2)

    return {
        "account_number": account_no,
        "bill_id": random.randint(100000000, 999999999),
        "bill_date": datetime.now().date(),
        "consumption_kwh": consumption,
        "rate_per_kwh": rate,
        "total_amount": total,
    }

def save_to_file(data, path):
    """Save processed bills to the same format as input file (CSV or Excel)."""
    if path.endswith(".csv"):
        pd.DataFrame(data).to_csv(path, index=False)
    elif path.endswith(".xlsx"):
        pd.DataFrame(data).to_excel(path, index=False)
    else:
        raise ValueError("Unsupported output file format. Must be .csv or .xlsx")
