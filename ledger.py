"""Offline CSV ledger. Python 3.10+, standard library only."""
import argparse
import csv
import json
import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

LOG = logging.getLogger("receipt-ledger")
RULES = {"Food": ("makan", "resto", "coffee", "kopi"),
         "Transport": ("grab", "gojek", "bensin", "parkir"),
         "Utilities": ("listrik", "internet", "air", "pln")}


def money(value):
    """Canonical decimal notation; no ambiguous locale guessing."""
    try:
        result = Decimal(value.strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError("amount must use decimal notation, e.g. -12500.50") from exc
    if not result.is_finite() or result.as_tuple().exponent < -2:
        raise ValueError("amount must be finite with at most two decimal places")
    if abs(result) > Decimal("999999999999.99"):
        raise ValueError("amount exceeds supported range")
    return result


def load_rules(path=None):
    if path is None:
        return RULES
    rules = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rules, dict) or not all(
        isinstance(k, str) and k.strip() and isinstance(v, list) and
        all(isinstance(w, str) and w.strip() for w in v)
        for k, v in rules.items()
    ):
        raise ValueError("rules must map nonempty categories to lists of nonempty keywords")
    return rules


def read_transactions(paths, rules, month=None):
    rows = []
    for path in paths:
        with Path(path).open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not {"date", "description", "amount"} <= set(reader.fieldnames):
                raise ValueError(f"{path}: required columns: date,description,amount")
            for line, row in enumerate(reader, 2):
                try:
                    if None in row or any(row.get(k) is None for k in ("date", "description", "amount")):
                        raise ValueError("incorrect column count")
                    raw_date = row["date"].strip()
                    parsed = date.fromisoformat(raw_date)
                    if parsed.isoformat() != raw_date:
                        raise ValueError("date must be YYYY-MM-DD")
                    description = row["description"].strip()
                    if not description or len(description) > 4096:
                        raise ValueError("description must contain 1..4096 characters")
                    amount = money(row["amount"])
                    category = next((name for name, words in rules.items()
                                     if any(word.casefold() in description.casefold() for word in words)), "Other")
                    if month is None or parsed.strftime("%Y-%m") == month:
                        rows.append({"date": raw_date, "description": description,
                                     "amount": amount, "category": category})
                except ValueError as exc:
                    raise ValueError(f"{path}:{line}: {exc}") from exc
    return rows


def summarize(rows):
    income = Decimal(0)
    expenses = Decimal(0)
    categories = defaultdict(lambda: Decimal(0))
    for row in rows:
        amount = row["amount"]
        if amount >= 0:
            income += amount
        else:
            expenses -= amount
            categories[row["category"]] -= amount
    return {"count": len(rows), "income": f"{income:.2f}",
            "expenses": f"{expenses:.2f}", "net": f"{income - expenses:.2f}",
            "categories": {k: f"{v:.2f}" for k, v in sorted(categories.items())}}


def markdown(report):
    lines = ["# Spending report", "", f"Transactions: {report['count']}",
             f"Income: {report['income']}", f"Expenses: {report['expenses']}",
             f"Net: {report['net']}", "", "| Category | Expenses |", "| --- | ---: |"]
    for category, amount in report["categories"].items():
        safe = category.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace("|", "&#124;").replace("\n", " ").replace("\r", " ")
        lines.append(f"| {safe} | {amount} |")
    return "\n".join(lines) + "\n"


def write_new(path, text):
    """Exclusive creation: never overwrite an existing user file."""
    with Path(path).open("x", encoding="utf-8") as handle:
        handle.write(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="CSV files or folders (nonrecursive)")
    parser.add_argument("--month", help="YYYY-MM")
    parser.add_argument("--rules", type=Path, help="JSON category -> keywords")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path, help="new output file; default stdout")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        if args.month:
            parsed = date.fromisoformat(args.month + "-01")
            if parsed.strftime("%Y-%m") != args.month:
                raise ValueError("month must be YYYY-MM")
        paths = []
        for item in args.inputs:
            if item.is_dir():
                paths.extend(sorted(item.glob("*.csv")))
            else:
                paths.append(item)
        paths = list(dict.fromkeys(path.resolve() for path in paths))
        if not paths:
            raise ValueError("no CSV files found")
        report = summarize(read_transactions(paths, load_rules(args.rules), args.month))
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else markdown(report)
        if args.output:
            write_new(args.output, text)
            LOG.info("Wrote %s (%s transactions)", args.output, report["count"])
        else:
            print(text, end="")
        return 0
    except (OSError, ValueError, csv.Error) as exc:
        LOG.error("%s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
