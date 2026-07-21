from datetime import date

import numpy as np
import pandas as pd


def load_tabular_data(source) -> pd.DataFrame:
    name = str(getattr(source, "name", source)).lower()
    if name.endswith(".csv"):
        return pd.read_csv(source)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(source)
    raise ValueError("Unsupported file type. Upload CSV or XLSX.")


def load_sample_data(rows: int = 360) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    products = [
        ("P001", "Ergo Mouse", "Accessories", 69),
        ("P002", "Mechanical Keyboard", "Accessories", 119),
        ("P003", "HD Webcam", "Video", 89),
        ("P004", "Wireless Headset", "Audio", 139),
        ("P005", "Conference Speaker", "Audio", 179),
    ]
    regions = ["Ireland", "United Kingdom", "Germany", "France"]
    start = pd.Timestamp(date.today()) - pd.Timedelta(days=365)
    records = []
    for index in range(rows):
        product_id, product_name, category, price = products[rng.integers(len(products))]
        records.append(
            {
                "order_id": f"O{index + 1:05d}",
                "order_date": start + pd.Timedelta(days=int(rng.integers(366))),
                "product_id": product_id,
                "product_name": product_name,
                "category": category,
                "region": regions[rng.integers(len(regions))],
                "customer_id": f"C{int(rng.integers(1, 121)):03d}",
                "quantity": int(rng.integers(1, 5)),
                "unit_price": price,
                "discount": float(rng.choice([0, 0, 0, 0.05, 0.1, 0.15])),
                "order_status": str(rng.choice(["Completed"] * 19 + ["Cancelled"])),
            }
        )
    return pd.DataFrame(records)
