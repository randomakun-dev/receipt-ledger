# Receipt Ledger
Offline spending reports from normalized CSV exports. No runtime dependencies, credentials or network calls.

## Quickstart
Python 3.10 or later:
```sh
python ledger.py examples/transactions.csv --month 2026-01
python ledger.py examples/transactions.csv --format json
python ledger.py private-data/ --output reports/january.md
```
Create the output parent directory first. Existing output files are never overwritten. Folder input includes lowercase *.csv files, nonrecursively.

Optional installed command:
```sh
python -m pip install .
receipt-ledger examples/transactions.csv
```

## Input contract
UTF-8 (optional BOM), comma delimiter, header `date,description,amount`. Dates strictly YYYY-MM-DD, amount uses decimal dot with at most two places; positive is income, negative is expense. Use one currency per invocation. Extra columns are ignored. Native bank/e-wallet formats are NOT automatically supported; normalize them first. Never upload real bank statements to a public repo.

## Demo
Bundled synthetic example: income 5000000.00, expenses 35000.50, net 4964999.50; Food 25000.50, Transport 10000.00.

## Custom categories
Create rules.json: `{"Groceries": ["market", "supermarket"], "Food": ["kopi"]}`.
```sh
python ledger.py examples/transactions.csv --rules rules.json
```
First matching category wins, case-insensitive substring matching. Unmatched transactions use Other. Only expenses are totaled by category.

## Validation and errors
Invalid files fail the entire report with exit 2 and source/line context where applicable; success exits 0. Output defaults to stdout, diagnostics to stderr. Exact decimal arithmetic avoids binary floating-point rounding. Do not combine overlapping exports without checking duplicates: only repeated input file paths are deduplicated, not transactions.

## Tests and quality checks
```sh
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
ruff check .
mypy ledger.py
python -m build
```
GitHub Actions runs these checks on Python 3.10, 3.12 and 3.13 and smoke-tests the installed wheel. Workflow can also be started manually from Actions. Configuration is not evidence of a passing CI run.

## Architecture
`ledger.py`: CLI -> rule loading -> CSV validation -> Decimal aggregation -> Markdown/JSON rendering -> stdout/exclusive file output. `tests/`: isolated synthetic fixtures; no real financial data. `examples/`: demo input. No database or service needed.

## Limitations and safety
Keyword categorization is heuristic. Transfers can inflate both income and spending; refunds count as income. Reports are not tax/accounting statements. Currency mixing is not detected. Very large exports are held in memory. An interrupted file write may leave a partial newly-created output; remove it manually before retrying. Keep sensitive inputs and reports outside source control. `.gitignore` covers suggested private-data/ and reports/ folders only.

## Roadmap
Explicit locale/native-export adapters, transfer pairing, configurable income categories, streaming aggregation, stronger static typing and additional integration tests.
