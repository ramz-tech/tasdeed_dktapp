import pandas as pd
import random
from datetime import datetime

def load_accounts(path):
    return pd.read_excel(path)

def generate_bill(account):
    if pd.isnull(account) or not str(account).isdigit():
        raise ValueError("Invalid or missing account number.")

    consumption = round(random.uniform(100, 1500), 2)
    rate = round(random.uniform(0.1, 0.3), 2)
    total = round(consumption * rate, 2)

    return {
        "account_number": account,
        "bill_id": random.randint(100000000, 999999999),
        "bill_date": datetime.now().date(),
        "consumption_kwh": consumption,
        "rate_per_kwh": rate,
        "total_amount": total,
    }

def save_to_excel(data, path):
    pd.DataFrame(data).to_excel(path, index=False)
