"""Generate fake bank and GL CSVs with planted exceptions. (Step 1)

Writes data/bank.csv and data/gl.csv for one month (October 2026).
Run from the project root:  python scripts/make_fake_data.py

ANSWER KEY
----------
Clean matches (40): every non-planted line pairs 1:1, same amount,
    bank date 0-3 days after GL date.                      -> Matched

Deposit in transit: gl.csv, 2026-10-30, JE-1047, 3250.00   -> Unmatched GL
Outstanding check #1099: gl.csv, 2026-10-24, JE-1043,
    -1875.00                                               -> Unmatched GL
Bank service fee: bank.csv, 2026-10-31, -15.00             -> Unmatched bank
Bank interest: bank.csv, 2026-10-31, 4.12                  -> Unmatched bank
Transposition: gl.csv 2026-10-06 JE-1012 1520.00           -> Unmatched GL
               bank.csv 2026-10-08 1250.00                 -> Unmatched bank
Duplicate check #1098: gl.csv 2026-10-12 JE-1024 and JE-1025, -2000.00;
    bank.csv 2026-10-14 -2000.00
    -> One GL line matched to the bank line, the other Unmatched GL.
       Both GL lines are identical (same date too), so which JE wins
       depends only on tie-break order; first found (JE-1024) is typical.
Same-amount trap: bank.csv 2026-10-17 500.00;
    gl.csv 2026-10-15 JE-1027 and 2026-10-18 JE-1030, 500.00 each
    -> One matched, one Unmatched GL. Decided in Step 3:
       "earliest" rule -> JE-1027 matches, JE-1030 unmatched
       "closest"  rule -> JE-1030 matches, JE-1027 unmatched

Totals:
    Unmatched bank (3 lines):  -15.00 + 4.12 + 1250.00          =  1,239.12
    Unmatched GL   (5 lines):  3250.00 - 1875.00 + 1520.00
                               - 2000.00 + 500.00               =  1,395.00
    Unmatched bank - unmatched GL                               =   -155.88
    (Must equal bank.csv total - gl.csv total, since every matched
     pair nets to zero.)

"""

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

# --- Settings -------------------------------------------------------------
SEED = 42                  # fixed seed -> identical CSVs on every run
YEAR, MONTH = 2026, 10
MONTH_START = date(YEAR, MONTH, 1)
MONTH_END = date(YEAR, MONTH, 31)
N_CLEAN_MATCHES = 40
MAX_BANK_LAG_DAYS = 3      # bank clears 0-3 days after the GL posting

# Amounts (in cents) used by the planted exceptions. Clean matches will never
# use these, so a random clean line can't accidentally collide with a trap.
# If you plant a new amount, add it here.
RESERVED_AMOUNTS_CENTS = {
    500_00,     # same-amount trap
    1_250_00,   # transposition (bank side)
    1_520_00,   # transposition (GL side)
    2_000_00,   # duplicate
    3_250_00,   # deposit in transit
    1_875_00,   # outstanding check
}

CUSTOMERS = ["Acme Corp", "Bluebird Supply", "Northwind Traders",
             "Summit Logistics", "Harbor Foods", "Pioneer Tools"]
VENDORS = ["Apex Paper", "Metro Utilities", "Keystone Freight",
           "Cobalt IT Services", "Redwood Leasing"]

# Folder this script lives in -> its parent is the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


# --- Building rows --------------------------------------------------------
def make_row(day: int, description: str, amount_cents: int) -> dict:
    """Return one transaction dict for the given day of the month."""
    return {
        "date": date(YEAR, MONTH, day),
        "description": description,
        "amount_cents": amount_cents,
    }


def random_unique_amount_cents(rng: random.Random, taken: set[int]) -> int:
    """Pick an amount between $100.00 and $9,999.99 not used before or reserved."""
    while True:
        cents = rng.randint(100_00, 9_999_99)
        if cents not in taken and cents not in RESERVED_AMOUNTS_CENTS:
            taken.add(cents)
            return cents


def make_clean_pairs(rng: random.Random) -> tuple[list[dict], list[dict]]:
    """Return (bank_rows, gl_rows): N_CLEAN_MATCHES transactions on both sides."""
    bank_rows: list[dict] = []
    gl_rows: list[dict] = []
    taken_amounts: set[int] = set()
    next_check_number = 1001

    # Latest GL date that still clears the bank inside the month, so no clean
    # item spills into the last days where deposits in transit live.
    latest_gl_offset = (MONTH_END - MONTH_START).days - MAX_BANK_LAG_DAYS - 1

    for _ in range(N_CLEAN_MATCHES):
        amount_cents = random_unique_amount_cents(rng, taken_amounts)
        gl_date = MONTH_START + timedelta(days=rng.randint(0, latest_gl_offset))
        bank_date = gl_date + timedelta(days=rng.randint(0, MAX_BANK_LAG_DAYS))

        if rng.random() < 0.5:  # customer deposit (cash in, positive)
            customer = rng.choice(CUSTOMERS)
            bank_description = f"DEPOSIT {customer.upper()}"
            gl_description = f"AR receipt {customer}"
        else:                   # check payment (cash out, negative)
            amount_cents = -amount_cents
            vendor = rng.choice(VENDORS)
            bank_description = f"CHECK {next_check_number}"
            gl_description = f"Chk {next_check_number} {vendor}"
            next_check_number += 1

        bank_rows.append({"date": bank_date, "description": bank_description,
                          "amount_cents": amount_cents})
        gl_rows.append({"date": gl_date, "description": gl_description,
                        "amount_cents": amount_cents})

    return bank_rows, gl_rows


def add_planted_exceptions(bank_rows: list[dict], gl_rows: list[dict]) -> None:
    """Append the known reconciling items to the bank and GL lists (in place).

    No randomness here on purpose: every planted item is spelled out exactly,
    so the answer key can be exact too.
    """
    # Deposit in transit: booked Oct 30, bank won't show it until November.
    gl_rows.append(make_row(30, "AR receipt Harbor Foods", 3_250_00))

    # Outstanding check: written and booked, vendor hasn't cashed it yet.
    gl_rows.append(make_row(24, "Chk 1099 Keystone Freight", -1_875_00))

    # Bank-only items: the GL doesn't know about these until the rec.
    bank_rows.append(make_row(31, "MONTHLY SERVICE FEE", -15_00))
    bank_rows.append(make_row(31, "INTEREST PAID", 4_12))

    # Transposition: same deposit, GL keyed 1,520.00 instead of 1,250.00.
    gl_rows.append(make_row(6, "AR receipt Pioneer Tools", 1_520_00))
    bank_rows.append(make_row(8, "DEPOSIT PIONEER TOOLS", 1_250_00))

    # Duplicate: check posted twice in the GL, cleared once at the bank.
    gl_rows.append(make_row(12, "Chk 1098 Metro Utilities", -2_000_00))
    gl_rows.append(make_row(12, "Chk 1098 Metro Utilities", -2_000_00))
    bank_rows.append(make_row(14, "CHECK 1098", -2_000_00))

    # Same-amount trap: one $500 bank deposit, two $500 GL candidates.
    # Oct 15 is earliest (2 days off); Oct 18 is closest (1 day off) and
    # dated AFTER the bank. Your Step 3 rule decides which one wins.
    bank_rows.append(make_row(17, "DEPOSIT BLUEBIRD SUPPLY", 500_00))
    gl_rows.append(make_row(15, "AR receipt Bluebird Supply", 500_00))
    gl_rows.append(make_row(18, "AR receipt Bluebird Supply", 500_00))


# --- Writing CSVs ---------------------------------------------------------
def rows_to_frame(rows: list[dict]) -> pd.DataFrame:
    """Build a date-sorted DataFrame from row dicts, with a dollar 'amount' column."""
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    # kind="stable" keeps same-date rows in the order they were added,
    # so JE numbers can't shuffle between runs.
    df = df.sort_values("date", kind="stable").reset_index(drop=True)
    # Format at the edge: cents -> dollars only for the file we write.
    df["amount"] = df["amount_cents"] / 100
    return df


def write_bank_csv(path: Path, rows: list[dict]) -> None:
    """Write bank rows to CSV, sorted by date."""
    df = rows_to_frame(rows)
    df[["date", "description", "amount"]].to_csv(
        path, index=False, date_format="%Y-%m-%d", float_format="%.2f")


def write_gl_csv(path: Path, rows: list[dict]) -> None:
    """Write GL rows to CSV, sorted by date, numbering them JE-1001, JE-1002, ..."""
    df = rows_to_frame(rows)
    df["je_id"] = "JE-" + (df.index + 1001).astype(str)
    df[["date", "je_id", "description", "amount"]].to_csv(
        path, index=False, date_format="%Y-%m-%d", float_format="%.2f")


def main() -> None:
    rng = random.Random(SEED)
    bank_rows, gl_rows = make_clean_pairs(rng)
    add_planted_exceptions(bank_rows, gl_rows)

    DATA_DIR.mkdir(exist_ok=True)
    write_bank_csv(DATA_DIR / "bank.csv", bank_rows)
    write_gl_csv(DATA_DIR / "gl.csv", gl_rows)
    print(f"Wrote {len(bank_rows)} bank rows and {len(gl_rows)} GL rows to {DATA_DIR}")


if __name__ == "__main__":
    main()
