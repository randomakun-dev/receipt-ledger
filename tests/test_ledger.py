import contextlib
import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
import ledger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.csv = self.root / "bank.csv"
        self.csv.write_text("date,description,amount\n2026-01-01,Gaji,5000000\n2026-01-02,Kopi,-25000.50\n2026-02-01,Grab,-10000\n", encoding="utf-8")

    def test_exact_totals(self):
        report = ledger.summarize(ledger.read_transactions([self.csv], ledger.RULES))
        self.assertEqual(report['expenses'], '35000.50')
        self.assertEqual(report['net'], '4964999.50')
        self.assertEqual(report['categories']['Food'], '25000.50')

    def test_month(self):
        self.assertEqual(len(ledger.read_transactions([self.csv], ledger.RULES, '2026-01')), 2)

    def test_invalid_money(self):
        for value in ('NaN', 'Infinity', '1,000', '1.001', '1e1000', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ledger.money(value)

    def test_money(self):
        self.assertEqual(ledger.money('-0.10'), Decimal('-0.10'))

    def test_missing_columns(self):
        self.csv.write_text('foo,bar\na,b\n')
        with self.assertRaisesRegex(ValueError, 'required columns'):
            ledger.read_transactions([self.csv], ledger.RULES)

    def test_bad_row(self):
        for row in ('2026-99-01,x,2', '2026-01-01,,2', '2026-01-01,x,2,extra', '2026-01-01,x'):
            self.csv.write_text('date,description,amount\n' + row + '\n')
            with self.subTest(row=row), self.assertRaises(ValueError):
                ledger.read_transactions([self.csv], ledger.RULES)

    def test_rules(self):
        path = self.root / 'rules.json'
        path.write_text('{"Custom": ["kopi"]}')
        self.assertEqual(ledger.read_transactions([self.csv], ledger.load_rules(path))[1]['category'], 'Custom')
        for content in ('[]', '{"X":"abc"}', '{"X":[""]}'):
            path.write_text(content)
            with self.assertRaises(ValueError):
                ledger.load_rules(path)

    def test_markdown_escaping(self):
        report = ledger.summarize([dict(amount=Decimal('-1'), category='<x>|\ny')])
        self.assertIn('&lt;x&gt;&#124; y', ledger.markdown(report))

    def test_cli_directory_and_duplicate_path(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            result = ledger.main([str(self.root), str(self.csv), '--format', 'json'])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stream.getvalue())['count'], 3)

    def test_output_no_overwrite(self):
        output = self.root / 'report.md'
        self.assertEqual(ledger.main([str(self.csv), '--output', str(output)]), 0)
        original = output.read_text()
        self.assertEqual(ledger.main([str(self.csv), '--output', str(output)]), 2)
        self.assertEqual(output.read_text(), original)

    def test_empty_folder_and_invalid_month(self):
        empty = self.root / 'empty'
        empty.mkdir()
        self.assertEqual(ledger.main([str(empty)]), 2)
        self.assertEqual(ledger.main([str(self.csv), '--month', '2026-13']), 2)

    def test_bom(self):
        self.csv.write_text('date,description,amount\n2026-01-01,kopi,-1\n', encoding='utf-8-sig')
        self.assertEqual(len(ledger.read_transactions([self.csv], ledger.RULES)), 1)


if __name__ == '__main__':
    unittest.main()
