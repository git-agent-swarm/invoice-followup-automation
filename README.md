# invoice-followup-automation

Small-business workflow automation demo: turn a basic invoice spreadsheet into
overdue follow-up drafts, a reminder CSV, and a clean HTML status dashboard.

This is the kind of repeatable admin workflow Kobey Dev Services can wire into
Gmail, Stripe, QuickBooks, Google Sheets, Airtable, or a CRM. The demo stays
local and safe: it writes drafts and reports only; it does not send email or
touch live accounts.

## What it does

- Reads invoice/customer data from CSV.
- Calculates paid, due-soon, and overdue status.
- Generates reminder email drafts by customer and urgency.
- Exports a follow-up queue as CSV.
- Builds a standalone HTML dashboard for owners or office staff.
- Runs with the Python standard library only.

## Run it

```bash
python invoice_followup.py --today 2026-06-13
```

Outputs are written to `output/`:

- `reminder_queue.csv` — invoices that need attention.
- `email_drafts.md` — ready-to-edit follow-up messages.
- `dashboard.html` — customer-facing proof of the reporting layer.

Use a different CSV:

```bash
python invoice_followup.py --input data/sample_invoices.csv --out output --today 2026-06-13
```

## Sample input

```csv
invoice_id,customer_name,email,amount,due_date,status
INV-1001,Cedar & Stone Roofing,billing@cedarstone.example,1850.00,2026-06-01,unpaid
INV-1002,Red River Fitness,owner@redriverfit.example,620.00,2026-06-20,unpaid
```

## Tests

```bash
python -m unittest discover -s tests
```

## Client-ready extensions

- Send approved drafts through Gmail or Outlook.
- Pull invoices from Stripe, QuickBooks, Square, or Google Sheets.
- Add SMS reminders through Twilio.
- Push overdue accounts into a CRM follow-up stage.
- Schedule the job every morning and email the dashboard to the owner.

## License

MIT
