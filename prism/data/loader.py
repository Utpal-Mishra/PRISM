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


def load_sample_data(rows: int = 900) -> pd.DataFrame:
    """Create deterministic synthetic business data for demonstrations and tests."""
    rng = np.random.default_rng(42)
    products = [
        ("P001", "Ergo Mouse", "Accessories", 69.0, 31.0),
        ("P002", "Mechanical Keyboard", "Accessories", 119.0, 57.0),
        ("P003", "HD Webcam", "Video", 89.0, 42.0),
        ("P004", "Wireless Headset", "Audio", 139.0, 66.0),
        ("P005", "Conference Speaker", "Audio", 179.0, 91.0),
    ]
    regions = ["Ireland", "United Kingdom", "Germany", "France"]
    channels = ["Direct", "Retail", "Marketplace", "Partner"]
    segments = ["Consumer", "SMB", "Enterprise"]
    start = pd.Timestamp(date.today()) - pd.Timedelta(days=730)
    records: list[dict[str, object]] = []

    for index in range(rows):
        day_offset = int(rng.integers(0, 731))
        order_date = start + pd.Timedelta(days=day_offset)
        product_id, product_name, category, price, base_cost = products[
            rng.integers(len(products))
        ]
        month = int(order_date.month)
        seasonal = 1.0 + 0.20 * np.sin(2 * np.pi * month / 12.0)
        maturity = 1.0 + 0.00035 * day_offset
        quantity = max(1, int(round(rng.normal(2.2 * seasonal * maturity, 0.9))))
        discount = float(rng.choice([0, 0, 0.05, 0.1, 0.15]))
        marketing_spend = max(20.0, float(rng.normal(95 + 8 * seasonal, 18)))
        lead_time = max(1.0, float(rng.normal(5.8, 1.7)))
        satisfaction = float(np.clip(rng.normal(4.35 - 0.08 * lead_time, 0.32), 1, 5))
        return_probability = 0.025 + 0.025 * (lead_time > 7) + 0.03 * (satisfaction < 3.7)
        returned = "Yes" if rng.random() < return_probability else "No"
        status = "Cancelled" if rng.random() < 0.045 else "Completed"
        unit_cost = max(1.0, float(rng.normal(base_cost, base_cost * 0.05)))

        records.append(
            {
                "order_id": f"O{index + 1:05d}",
                "order_date": order_date,
                "product_id": product_id,
                "product_name": product_name,
                "category": category,
                "region": regions[rng.integers(len(regions))],
                "channel": channels[rng.integers(len(channels))],
                "customer_segment": segments[rng.integers(len(segments))],
                "customer_id": f"C{int(rng.integers(1, 241)):03d}",
                "quantity": quantity,
                "unit_price": price,
                "unit_cost": round(unit_cost, 2),
                "discount": discount,
                "marketing_spend": round(marketing_spend, 2),
                "lead_time_days": round(lead_time, 2),
                "customer_satisfaction": round(satisfaction, 2),
                "returned": returned,
                "order_status": status,
            }
        )
    return pd.DataFrame(records)
