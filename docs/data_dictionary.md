# Data dictionary

| Column | Type | Required | Description |
|---|---|---:|---|
| order_id | text | Yes | Unique order identifier |
| order_date | date | Yes | Order date |
| product_id | text | Yes | Product identifier |
| product_name | text | Yes | Product name |
| category | text | Yes | Product category |
| region | text | Yes | Commercial region |
| customer_id | text | Yes | Customer identifier |
| quantity | number | Yes | Units ordered |
| unit_price | number | Yes | Price per unit |
| order_status | text | Yes | Completed or Cancelled |
| discount | decimal | No | Discount from 0 to 1 |
