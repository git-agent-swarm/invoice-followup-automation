from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import unittest

from invoice_followup import classify_all, dashboard_metrics, load_invoices, run


ROOT = Path(__file__).resolve().parents[1]


class InvoiceFollowupTests(unittest.TestCase):
    def test_classifies_overdue_due_soon_and_paid(self) -> None:
        invoices = load_invoices(ROOT / "data/sample_invoices.csv")
        statuses = classify_all(invoices, date(2026, 6, 13))
        labels = {status.invoice.invoice_id: status.label for status in statuses}

        self.assertEqual(labels["INV-1001"], "overdue")
        self.assertEqual(labels["INV-1002"], "due_soon")
        self.assertEqual(labels["INV-1005"], "not_due")
        self.assertEqual(labels["INV-1006"], "paid")

    def test_dashboard_metrics(self) -> None:
        invoices = load_invoices(ROOT / "data/sample_invoices.csv")
        statuses = classify_all(invoices, date(2026, 6, 13))
        metrics = dashboard_metrics(statuses)

        self.assertEqual(metrics["open_count"], 5)
        self.assertEqual(metrics["overdue_count"], 3)
        self.assertEqual(metrics["due_soon_count"], 1)
        self.assertAlmostEqual(metrics["total_overdue"], 4070.50)

    def test_run_writes_expected_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            outputs = run(ROOT / "data/sample_invoices.csv", out_dir, date(2026, 6, 13))

            self.assertTrue(outputs["queue"].exists())
            self.assertTrue(outputs["drafts"].exists())
            self.assertTrue(outputs["dashboard"].exists())

            with outputs["queue"].open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 4)
            self.assertIn("Invoice INV-1001 is 12 days overdue", outputs["drafts"].read_text())
            self.assertIn("Invoice Follow-up Dashboard", outputs["dashboard"].read_text())


if __name__ == "__main__":
    unittest.main()
