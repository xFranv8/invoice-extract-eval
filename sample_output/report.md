# Extraction accuracy report

- Extractor: `rules`
- Documents: 53
- Fully correct documents: 75%
- Sent to human review: 13 of 53
- Errors caught by the review queue: 100%
- Auto-accepted documents that still had an error: 0%

## Accuracy per field

| Field | Accuracy |
|---|---|
| invoice_number | 75% |
| invoice_date | 75% |
| supplier_name | 75% |
| supplier_vat_id | 94% |
| customer_name | 75% |
| currency | 94% |
| subtotal | 75% |
| tax_amount | 94% |
| total | 94% |

## Per layout

| Layout | Docs | Fully correct | Sent to review |
|---|---|---|---|
| classic_es | 10 | 10 | 0 |
| compact_codes | 10 | 10 | 0 |
| held_out_vendor | 10 | 0 | 10 |
| modern_en | 10 | 10 | 0 |
| reverse_charge_eu | 10 | 10 | 0 |
| scanned | 3 | 0 | 3 |

## Review queue

| Document | Reasons |
|---|---|
| held_out_vendor_00.pdf | missing invoice_number; missing invoice_date; cannot cross-check total (subtotal or tax missing) |
| held_out_vendor_01.pdf | missing invoice_number; missing invoice_date; cannot cross-check total (subtotal or tax missing) |
| held_out_vendor_02.pdf | missing invoice_number; missing invoice_date; cannot cross-check total (subtotal or tax missing) |
| held_out_vendor_03.pdf | missing invoice_number; missing invoice_date; cannot cross-check total (subtotal or tax missing) |
| held_out_vendor_04.pdf | missing invoice_number; missing invoice_date; cannot cross-check total (subtotal or tax missing) |
| held_out_vendor_05.pdf | missing invoice_number; missing invoice_date; cannot cross-check total (subtotal or tax missing) |
| held_out_vendor_06.pdf | missing invoice_number; missing invoice_date; cannot cross-check total (subtotal or tax missing) |
| held_out_vendor_07.pdf | missing invoice_number; missing invoice_date; cannot cross-check total (subtotal or tax missing) |
| held_out_vendor_08.pdf | missing invoice_number; missing invoice_date; cannot cross-check total (subtotal or tax missing) |
| held_out_vendor_09.pdf | missing invoice_number; missing invoice_date; cannot cross-check total (subtotal or tax missing) |
| scanned_00.pdf | no text extracted (image-only PDF?): needs OCR or a vision model |
| scanned_01.pdf | no text extracted (image-only PDF?): needs OCR or a vision model |
| scanned_02.pdf | no text extracted (image-only PDF?): needs OCR or a vision model |

## Field errors

| Document | Wrong fields | In review queue |
|---|---|---|
| held_out_vendor_00.pdf | invoice_number, invoice_date, supplier_name, customer_name, subtotal | yes |
| held_out_vendor_01.pdf | invoice_number, invoice_date, supplier_name, customer_name, subtotal | yes |
| held_out_vendor_02.pdf | invoice_number, invoice_date, supplier_name, customer_name, subtotal | yes |
| held_out_vendor_03.pdf | invoice_number, invoice_date, supplier_name, customer_name, subtotal | yes |
| held_out_vendor_04.pdf | invoice_number, invoice_date, supplier_name, customer_name, subtotal | yes |
| held_out_vendor_05.pdf | invoice_number, invoice_date, supplier_name, customer_name, subtotal | yes |
| held_out_vendor_06.pdf | invoice_number, invoice_date, supplier_name, customer_name, subtotal | yes |
| held_out_vendor_07.pdf | invoice_number, invoice_date, supplier_name, customer_name, subtotal | yes |
| held_out_vendor_08.pdf | invoice_number, invoice_date, supplier_name, customer_name, subtotal | yes |
| held_out_vendor_09.pdf | invoice_number, invoice_date, supplier_name, customer_name, subtotal | yes |
| scanned_00.pdf | invoice_number, invoice_date, supplier_name, supplier_vat_id, customer_name, currency, subtotal, tax_amount, total | yes |
| scanned_01.pdf | invoice_number, invoice_date, supplier_name, supplier_vat_id, customer_name, currency, subtotal, tax_amount, total | yes |
| scanned_02.pdf | invoice_number, invoice_date, supplier_name, supplier_vat_id, customer_name, currency, subtotal, tax_amount, total | yes |
