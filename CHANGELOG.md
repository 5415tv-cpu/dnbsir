# Changelog

## 2026-02-09 — Code Audit & Bug Fix Sprint

### webhook_app.py — 8 bugs fixed
- Added missing `_extract_value()` function definition for dangling code block
- Added missing `import openpyxl` for Excel export endpoint
- Fixed double request body consumption in `payment_webhook` (`await request.json()` -> `json.loads(payload)`)
- Fixed XSS vulnerability in 404 handler — added `html_escape()` on `request.url.path`
- Removed duplicate imports (`sms_manager`, `Form`, `UploadFile/File`)
- Removed unused code (`OrderRequest` model, `get_card_session`, `import random`)
- Consolidated all imports at top of file (`hmac`, `hashlib`, `json`, `logen`, `gsheet`)

### db_manager.py — 27 missing wrapper functions added
- Dashboard & Stats: `get_today_stats`
- Auto Reply: `update_store_auto_reply`
- Wallet: `charge_wallet`
- Products: `save_product`, `get_all_products`, `get_product_detail`, `decrease_product_inventory`
- Orders: `save_order`, `get_order_by_id`, `update_order_status`, `update_payment_method`, `update_order_tracking`
- Tax & Expenses: `get_tax_report_data`, `get_tax_stats`, `get_monthly_expenses`, `save_expense`
- Ledger: `get_integrated_ledger`, `lock_ledger`
- Customer CRM: `get_customer`, `get_customer_by_phone`, `save_customer`, `update_customer_field`, `increment_customer_order`

### db_sqlite.py — 9 new implementations + 1 table + 1 column
- New functions: `charge_wallet`, `decrease_product_inventory`, `get_tax_report_data`, `update_order_status`, `get_customer`, `get_customer_by_phone`, `save_customer`, `update_customer_field`, `increment_customer_order`
- New table: `customers` (CRM) with unique constraint on `(customer_id, store_id)`
- New column: `products.inventory` (default 100)

### sms_manager.py — 7 missing imports added
- `requests`, `time`, `datetime`, `uuid`, `hmac`, `hashlib`, `db_manager as db`

### server/logen_service.py — duplicate code removed & bugs fixed
- Removed ~90 lines of duplicated imports, constants, and functions
- Moved `LOGEN_API_URL` and `LOGEN_API_KEY` constants to top of file
- Fixed `db.update_tracking_number` -> `db.update_order_tracking` (3 call sites)
- Added missing return values to `process_refund`

### Summary
| Metric                    | Count |
|---------------------------|-------|
| Files modified            | 6     |
| Bugs fixed (webhook_app)  | 8     |
| Missing functions added   | 36    |
| Missing imports added     | 8     |
| Duplicate code removed    | ~90 lines |
| Security fixes            | 2 (XSS, double body read) |
| New DB tables             | 1 (customers) |
| New DB columns            | 1 (products.inventory) |
