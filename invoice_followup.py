#!/usr/bin/env python3
"""Generate invoice reminder drafts and a simple owner dashboard."""

from __future__ import annotations

import argparse
import csv
import html
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from statistics import mean


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    customer_name: str
    email: str
    amount: float
    due_date: date
    status: str


@dataclass(frozen=True)
class InvoiceStatus:
    invoice: Invoice
    label: str
    days_delta: int

    @property
    def needs_followup(self) -> bool:
        return self.label in {"overdue", "due_soon"}


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def load_invoices(path: Path) -> list[Invoice]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = csv.DictReader(fh)
        invoices: list[Invoice] = []
        for row in rows:
            invoices.append(
                Invoice(
                    invoice_id=row["invoice_id"].strip(),
                    customer_name=row["customer_name"].strip(),
                    email=row["email"].strip(),
                    amount=float(row["amount"]),
                    due_date=parse_date(row["due_date"].strip()),
                    status=row["status"].strip().lower(),
                )
            )
    return invoices


def classify_invoice(invoice: Invoice, today: date, due_soon_days: int = 7) -> InvoiceStatus:
    if invoice.status == "paid":
        return InvoiceStatus(invoice, "paid", 0)

    days_delta = (today - invoice.due_date).days
    if days_delta > 0:
        return InvoiceStatus(invoice, "overdue", days_delta)
    if -days_delta <= due_soon_days:
        return InvoiceStatus(invoice, "due_soon", abs(days_delta))
    return InvoiceStatus(invoice, "not_due", abs(days_delta))


def classify_all(invoices: list[Invoice], today: date) -> list[InvoiceStatus]:
    return [classify_invoice(invoice, today) for invoice in invoices]


def reminder_subject(status: InvoiceStatus) -> str:
    invoice = status.invoice
    if status.label == "overdue":
        return f"Invoice {invoice.invoice_id} is {status.days_delta} days overdue"
    return f"Invoice {invoice.invoice_id} is due in {status.days_delta} days"


def reminder_body(status: InvoiceStatus) -> str:
    invoice = status.invoice
    amount = f"${invoice.amount:,.2f}"
    if status.label == "overdue":
        timing = f"was due on {invoice.due_date:%b %-d, %Y}"
        ask = "Could you send an update on payment timing?"
    else:
        timing = f"is due on {invoice.due_date:%b %-d, %Y}"
        ask = "This is a quick reminder before the due date."

    return (
        f"Hi {invoice.customer_name},\n\n"
        f"{ask} Invoice {invoice.invoice_id} for {amount} {timing}.\n\n"
        "If payment has already been sent, thank you and please ignore this note.\n\n"
        "Thanks,\nKobey Dev Services"
    )


def write_reminder_queue(statuses: list[InvoiceStatus], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "invoice_id",
                "customer_name",
                "email",
                "amount",
                "due_date",
                "status",
                "days_delta",
                "subject",
            ],
        )
        writer.writeheader()
        for status in statuses:
            if not status.needs_followup:
                continue
            invoice = status.invoice
            writer.writerow(
                {
                    "invoice_id": invoice.invoice_id,
                    "customer_name": invoice.customer_name,
                    "email": invoice.email,
                    "amount": f"{invoice.amount:.2f}",
                    "due_date": invoice.due_date.isoformat(),
                    "status": status.label,
                    "days_delta": status.days_delta,
                    "subject": reminder_subject(status),
                }
            )


def write_email_drafts(statuses: list[InvoiceStatus], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sections: list[str] = ["# Invoice Follow-up Drafts\n"]
    for status in statuses:
        if not status.needs_followup:
            continue
        invoice = status.invoice
        sections.append(
            "\n".join(
                [
                    f"## {invoice.invoice_id} — {invoice.customer_name}",
                    f"To: {invoice.email}",
                    f"Subject: {reminder_subject(status)}",
                    "",
                    reminder_body(status),
                    "",
                    "---",
                    "",
                ]
            )
        )
    path.write_text("\n".join(sections), encoding="utf-8")


def dashboard_metrics(statuses: list[InvoiceStatus]) -> dict[str, float]:
    open_statuses = [status for status in statuses if status.label != "paid"]
    overdue = [status for status in statuses if status.label == "overdue"]
    due_soon = [status for status in statuses if status.label == "due_soon"]
    total_open = sum(status.invoice.amount for status in open_statuses)
    total_overdue = sum(status.invoice.amount for status in overdue)
    average_overdue_days = mean([status.days_delta for status in overdue]) if overdue else 0
    return {
        "open_count": len(open_statuses),
        "overdue_count": len(overdue),
        "due_soon_count": len(due_soon),
        "total_open": total_open,
        "total_overdue": total_overdue,
        "average_overdue_days": average_overdue_days,
    }


def write_dashboard(statuses: list[InvoiceStatus], path: Path, today: date) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = dashboard_metrics(statuses)
    rows = []
    for status in statuses:
        invoice = status.invoice
        rows.append(
            "<tr>"
            f"<td>{html.escape(invoice.invoice_id)}</td>"
            f"<td>{html.escape(invoice.customer_name)}</td>"
            f"<td>${invoice.amount:,.2f}</td>"
            f"<td>{invoice.due_date.isoformat()}</td>"
            f"<td><span class='badge {status.label}'>{status.label.replace('_', ' ')}</span></td>"
            f"<td>{status.days_delta}</td>"
            "</tr>"
        )

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Invoice Follow-up Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; color: #17202a; background: #f5f7fb; }}
    main {{ max-width: 1040px; margin: 0 auto; padding: 32px 20px; }}
    h1 {{ margin-bottom: 4px; }}
    .muted {{ color: #5d6d7e; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 24px 0; }}
    .metric {{ background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 16px; }}
    .metric strong {{ display: block; font-size: 28px; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d9e2ec; }}
    th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #e8eef5; }}
    th {{ background: #edf3f8; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 4px 10px; font-size: 12px; font-weight: 700; }}
    .overdue {{ background: #ffe5e5; color: #a11f1f; }}
    .due_soon {{ background: #fff3cd; color: #7a5a00; }}
    .not_due {{ background: #e8f4ff; color: #1f5f91; }}
    .paid {{ background: #e8f7ee; color: #1d6b38; }}
  </style>
</head>
<body>
  <main>
    <h1>Invoice Follow-up Dashboard</h1>
    <p class="muted">Generated {today.isoformat()} by Kobey Dev Services.</p>
    <section class="metrics">
      <div class="metric">Open invoices<strong>{metrics["open_count"]:.0f}</strong></div>
      <div class="metric">Overdue invoices<strong>{metrics["overdue_count"]:.0f}</strong></div>
      <div class="metric">Due soon<strong>{metrics["due_soon_count"]:.0f}</strong></div>
      <div class="metric">Open balance<strong>${metrics["total_open"]:,.2f}</strong></div>
      <div class="metric">Overdue balance<strong>${metrics["total_overdue"]:,.2f}</strong></div>
      <div class="metric">Avg overdue days<strong>{metrics["average_overdue_days"]:.1f}</strong></div>
    </section>
    <table>
      <thead>
        <tr>
          <th>Invoice</th>
          <th>Customer</th>
          <th>Amount</th>
          <th>Due date</th>
          <th>Status</th>
          <th>Days</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </main>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")


def run(input_path: Path, out_dir: Path, today: date) -> dict[str, Path]:
    invoices = load_invoices(input_path)
    statuses = classify_all(invoices, today)
    outputs = {
        "queue": out_dir / "reminder_queue.csv",
        "drafts": out_dir / "email_drafts.md",
        "dashboard": out_dir / "dashboard.html",
    }
    write_reminder_queue(statuses, outputs["queue"])
    write_email_drafts(statuses, outputs["drafts"])
    write_dashboard(statuses, outputs["dashboard"], today)
    return outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate invoice follow-up drafts and dashboard.")
    parser.add_argument("--input", type=Path, default=Path("data/sample_invoices.csv"))
    parser.add_argument("--out", type=Path, default=Path("output"))
    parser.add_argument("--today", type=parse_date, default=date.today())
    return parser


def main() -> int:
    args = build_parser().parse_args()
    outputs = run(args.input, args.out, args.today)
    for label, path in outputs.items():
        print(f"{label:10} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
