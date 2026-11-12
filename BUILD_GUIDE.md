# Recon Tool V1: Step-by-Step Build Guide

Nov 11, 2026 · @Jonny

## Overview

V1 is a command-line tool that reconciles a bank statement against the GL cash account and reports what ties out and what doesn't. You build it in seven steps (0–6), one Claude Code session per step, with best practices learned along the way.

**Command:** `python -m recon data/bank.csv data/gl.csv`

**Outputs:**

- `matched.csv` — bank/GL pairs that tie out
- `unmatched_bank.csv` and `unmatched_gl.csv` — the reconciling items
- A printed summary: counts, totals per side, unreconciled difference

**V1 matching rule:** same amount, dates within ±3 days, one-to-one only. Many-to-one and fuzzy matching wait for V2.

| Claude Code does | You do |
| --- | --- |
| Project scaffolding and folder setup | The matching logic (`matcher.py`) |
| The fake-data generator script | Data cleaning rules |
| The first example test | The remaining tests |
| Explaining git and tools as they come up | The summary math and the README |

**Final folder structure:**

```
recon-tool/
├── .gitignore
├── README.md
├── requirements.txt
├── CLAUDE.md
├── data/              # sample CSVs
├── output/            # generated results (gitignored)
├── scripts/
│   └── make_fake_data.py
├── recon/             # the package
│   ├── __init__.py
│   ├── __main__.py    # command-line entry point
│   ├── loader.py      # read + clean
│   ├── matcher.py     # your matching logic
│   └── report.py      # outputs + summary
└── tests/
    └── test_matcher.py
```

## How to use this guide with Claude Code

One step per session. Start each session by telling Claude Code which step you're on, and finish it with a commit.

**Turn on Learning mode.** In Claude Code, open `/config` → Output style → Learning. Claude Code will leave `TODO(human)` markers for you to fill in, then wait for you. ([docs](https://code.claude.com/docs/en/output-styles))

**Create `CLAUDE.md` in the project folder** (Step 0 does this). Claude Code reads it every session:

```markdown
# About me
Beginner Python dev (Codecademy Python 3, some Godot/GDScript). Former accountant
pivoting into tech. My goal is to LEARN, not just ship.

# How to work with me
- Before writing code, explain the plan and why. Let me push back.
- Have me write the core logic; you handle boilerplate and setup.
- When I'm stuck, give a hint first, not the answer.
- Explain new concepts (libraries, patterns, git commands) the first time they come up.
- Review my code like a senior dev would: what works, what's fragile, what's unidiomatic.

# Project rules
- Follow BUILD_GUIDE steps in order; don't jump ahead.
- I write recon/matcher.py. Don't write matching logic unless I ask; give hints.
- Point out best practices as they come up and explain why they matter.
- Remind me to commit at sensible checkpoints.
```

**Session kickoff prompt** (swap in the step number):

> We're on Step N of my recon tool build guide. Here's the step: \[paste the step\]. Walk me through it, explain each thing and why it's a best practice, and have me write the parts marked "You write."

**Your rules for every session:**

1. Write your own rough plan before asking Claude anything.
2. Never accept code you can't explain. Ask "explain this line by line" whenever you need it.
3. Type commands yourself instead of letting Claude run them, at least the first few times.
4. End every session with a commit and one sentence in a learning log (what you learned, what confused you).

## Step 0: Setup

**Goal:** an empty, version-controlled project on GitHub with its own Python environment. **Time:** about 1–2 hours.

**Install (once per computer):**

- [x] Python 3.12 or newer from python.org (Windows: tick "Add Python to PATH")
- [x] Git from git-scm.com
- [x] VS Code, plus its Python extension
- [x] Claude Code (follow the install steps at code.claude.com)
- [x] A GitHub account

**Create the project:**

- [x] Make a folder called `recon-tool`, open it in VS Code, and open the terminal (View → Terminal)
- [x] Create a virtual environment: `python -m venv .venv` (Mac: `python3`)
- [x] Activate it — Mac: `source .venv/bin/activate` · Windows: `.venv\Scripts\activate`. You'll see `(.venv)` in the prompt.
- [x] Install packages: `pip install pandas pytest`
- [x] Save the exact versions: `pip freeze > requirements.txt`
- [x] Start Claude Code, switch to Learning mode, and have it scaffold the folders from the Overview plus `CLAUDE.md` and `.gitignore`
- [x] Check `.gitignore` contains at least `.venv/`, `__pycache__/`, and `output/`
- [x] Start git: `git init`, then `git add .`, then `git commit -m "Initial project structure"`
- [x] Create an empty repo on GitHub named `recon-tool` and run the three push commands GitHub shows you

**Done when:** your GitHub page shows the folders, and `git status` says "nothing to commit."

**Best practices in this step:**

- **Virtual environment** — each project gets its own packages, so projects can't break each other. Activate it every time you work.
- **requirements.txt** — anyone (including future you) can rebuild the environment with `pip install -r requirements.txt`.
- **.gitignore** — keeps junk and generated files out of the repo.
- **Commit early and often** — small commits with clear messages ("Add date parsing to loader") make mistakes cheap to undo.

## Step 1: Fake data with planted exceptions

**Goal:** `scripts/make_fake_data.py` writes `data/bank.csv` and `data/gl.csv` for one month, with known problems planted in them, so you can tell whether the tool catches them. **Time:** 1–2 hours.

**File formats** (V1 uses the same sign on both sides: cash in is positive, cash out is negative):

```csv
date,description,amount
2026-10-02,DEPOSIT ACME CORP,4250.00
2026-10-03,CHECK 1042,-1250.00
```

```csv
date,je_id,description,amount
2026-10-01,JE-1001,AR receipt Acme,4250.00
2026-10-02,JE-1002,Chk 1042 Vendor X,-1250.00
```

**Plant these exceptions:**

| Exception | Where it shows up | Expected result |
| --- | --- | --- |
| \~40 clean matches, dates 0–3 days apart | Both files | Matched |
| Deposit in transit | GL only, last 2 days of month | Unmatched GL |
| Outstanding check | GL only | Unmatched GL |
| Bank fee and interest | Bank only | Unmatched bank |
| Transposition: GL 1,520.00 vs bank 1,250.00 | Both files, different amounts | Unmatched on both sides |
| Duplicate GL entry | GL twice, bank once | One matched, one unmatched GL |
| Same-amount trap: two $500 GL lines near one $500 bank line | Both files | Your design decision (Step 3) |

**Steps:**

- [ ] Ask Claude Code to explain the plan for the script, then have it write the clean-match part
- [ ] **You write:** the function that adds the planted exceptions (Claude can leave it as a `TODO(human)`)
- [ ] Use a fixed random seed so the same data comes out every run
- [ ] Run it: `python scripts/make_fake_data.py`, then open both CSVs and check that every planted exception is there
- [ ] Write the expected results down (an "answer key") in a comment at the top of the script
- [ ] Commit: "Add fake data generator"

**Done when:** you can point to every planted exception in the CSVs and say what the tool should do with it.

**Best practices in this step:**

- **Reproducible test data** — a fixed seed means a bug you see today shows up again tomorrow.
- **Know the answer before you build** — the answer key turns into your tests in Step 5.
- **Never use real financial data in a public repo** — fake data keeps client and employer information out of GitHub.

## Step 2: Load and clean the data

**Goal:** `recon/loader.py` turns each CSV into a clean pandas DataFrame with real dates, amounts in integer cents, and a unique ID per row, or stops with a clear error. **Time:** 2–3 hours.

**Steps:**

- [ ] Have Claude Code explain pandas basics as you go: `read_csv`, columns, dtypes, `.head()`
- [ ] Write `load_bank(path)` and `load_gl(path)`, each returning a DataFrame
- [ ] Parse dates with `pd.to_datetime`
- [ ] Convert amounts to integer cents: `(df["amount"] * 100).round().astype(int)`
- [ ] Add a `row_id` column (e.g. `B001`, `G001`) so every line can be traced back
- [ ] **You write:** a `validate(df)` function that raises a clear error for missing columns, blank dates, or blank amounts
- [ ] Test it by hand: break a copy of the CSV on purpose and confirm the error message tells you exactly what's wrong
- [ ] Commit: "Add loader with validation"

**Done when:** both files load in a Python session, `df.dtypes` shows datetime and int columns, and a broken file fails loudly.

**Best practices in this step:**

- **Never store money as floats.** In Python `0.1 + 0.2` gives `0.30000000000000004`. Integer cents make sums exact. Convert back to dollars only for display.
- **Validate inputs at the edge.** Check data where it enters the program, so everything downstream can trust it.
- **Fail loudly.** A crash with a clear message beats a reconciliation that looks finished but is wrong.
- **Functions with docstrings and type hints:** `def load_bank(path: str) -> pd.DataFrame:`, with a one-line docstring saying what it returns.

## Step 3: Matching logic (you write this)

**Goal:** `recon/matcher.py` takes the two clean DataFrames and returns matched pairs plus the unmatched items on each side. You write this file; Claude Code only gives hints and reviews it. **Time:** 3–5 hours, likely over two sessions.

**The function you're building:**

```python
def match(bank: pd.DataFrame, gl: pd.DataFrame, date_window_days: int = 3) -> MatchResult:
    """One-to-one match on exact amount within a date window."""
```

`MatchResult` is a small class (a dataclass) holding three DataFrames: `matched`, `unmatched_bank`, `unmatched_gl`. Ask Claude Code to explain dataclasses before you write it. This is good practice with classes.

**Steps:**

- [ ] On paper first: write the matching steps in plain English (pseudocode) before any code
- [ ] Answer the design questions below in writing, then put your answers in the function's docstring
- [ ] Write the simplest version: loop through bank rows, find GL rows with the same amount inside the window, take one, and mark it used
- [ ] Run it on the fake data and compare against your Step 1 answer key
- [ ] Ask Claude Code for a senior-dev review of your code, then refactor based on it
- [ ] Commit after the simple version works, and again after the refactor

**Design questions to answer before coding:**

1. A $500 bank line on the 3rd has $500 GL candidates on the 2nd and the 5th. Which one wins: closest date, earliest date, or flag both for review?
2. Once a GL line is matched, how do you stop it from matching again? (This is the duplicate-entry case.)
3. Is the window ±3 days, or should the GL date always come on or before the bank date? Think about deposits in transit.
4. Does the order you loop through bank rows change the results? If it does, is that acceptable?

**Done when:** results match your answer key for every planted exception, and you can explain every line.

**Best practices in this step:**

- **Pure functions** — `match()` takes data in and returns results. No file reading, no printing. That makes it easy to test.
- **Make it work, then make it right** — get a clumsy version passing first, then clean it up.
- **No magic numbers** — `date_window_days` is a parameter, not a `3` buried in the code.
- **Descriptive names** — `candidates`, `used_gl_ids`, `days_apart`, not `x`, `temp`, `lst`.

## Step 4: Outputs, summary, and the command line

**Goal:** `recon/report.py` writes the three CSVs and prints a summary that proves the rec ties. `recon/__main__.py` connects everything so `python -m recon data/bank.csv data/gl.csv` runs start to finish. **Time:** 2–3 hours.

**The proof the summary must show:** every matched pair nets to zero, so the whole difference between the two sides has to be explained by the unmatched items.

```latex
\text{Bank total} - \text{GL total} = \sum \text{Unmatched bank} - \sum \text{Unmatched GL}
```

**Target summary output:**

```
RECONCILIATION SUMMARY
Bank lines: 46   GL lines: 47
Matched pairs: 41
Unmatched bank: 5   ($-37.50)
Unmatched GL:   6   ($5,880.00)
Bank total - GL total:       $-5,917.50
Explained by unmatched items: $-5,917.50
Status: TIES
```

**Steps:**

- [ ] Have Claude Code write `write_outputs(result, out_dir)` and explain `pathlib` and creating the `output/` folder
- [ ] **You write:** `summarize(bank, gl, result)`, which calculates the figures above and the TIES / DOES NOT TIE check
- [ ] Format cents as dollars only at print time: `f"${cents / 100:,.2f}"`
- [ ] Have Claude Code explain `argparse` and write `__main__.py` with it, so the command accepts the two file paths
- [ ] Run the full command and check every output file against your answer key
- [ ] Commit: "Add reporting and CLI"

**Done when:** one command produces all three files and a summary that says TIES.

**Best practices in this step:**

- **Separation of concerns** — loading, matching, and reporting each live in their own file. `__main__.py` only wires them together.
- **Self-checking output** — the program proves its own math, the same way a rec shows its own tie-out.
- **Format at the edge** — keep numbers as cents everywhere and turn them into dollar strings only when displaying them.

## Step 5: Tests with pytest

**Goal:** `tests/test_matcher.py` checks every matching rule against tiny hand-built datasets, so you can change code later and know right away if something broke. **Time:** 2–3 hours.

**Example test (Claude Code writes this first one):**

```python
def test_exact_match_within_window():
    bank = make_bank([("2026-10-03", 50000)])
    gl = make_gl([("2026-10-01", 50000)])
    result = match(bank, gl)
    assert len(result.matched) == 1
    assert result.unmatched_bank.empty
    assert result.unmatched_gl.empty
```

**Steps:**

- [ ] Have Claude Code write the example test plus small `make_bank` / `make_gl` helper functions, and explain the arrange → act → assert pattern
- [ ] Run the tests: `python -m pytest` (watch it pass, then break `match()` on purpose and watch it fail)
- [ ] **You write** one test per row of your Step 1 answer key:
  - [ ] Dates outside the window don't match
  - [ ] Bank-only fee comes out as unmatched bank
  - [ ] Transposed amounts stay unmatched on both sides
  - [ ] A duplicate GL entry matches once and leaves one unmatched
  - [ ] The same-amount trap resolves the way your Step 3 decision says
  - [ ] The summary proof ties
- [ ] Commit: "Add matcher tests"

**Done when:** all tests pass, and each planted exception has its own test.

**Best practices in this step:**

- **One behavior per test**, named for what it checks. A failing test's name tells you what broke.
- **Small, hand-built inputs** — three rows you can check in your head beat 50 rows of fake data.
- **Run tests before every commit** — this habit is what lets you refactor in V2 without fear.
- **Use `python -m pytest`** rather than bare `pytest`. It runs from the project folder, so `import recon` works.

## Step 6: README and push to GitHub

**Goal:** a README that lets a hiring manager understand the project in 60 seconds and a stranger run it in 5 minutes. **Time:** 1–2 hours.

**README outline (you write it; Claude Code reviews it):**

1. **What it is** — one sentence: "Python tool that reconciles bank activity to the GL cash account and isolates reconciling items."
2. **Why it exists** — two or three sentences on the real problem, from your experience running high-volume reconciliations.
3. **Quick start** — clone, create the venv, `pip install -r requirements.txt`, generate data, run the command.
4. **Sample output** — paste the summary from Step 4.
5. **How matching works** — the V1 rule and your design decisions from Step 3, in plain English.
6. **Running tests** — `python -m pytest`.
7. **Roadmap** — the V2 items below.

**Steps:**

- [ ] Write the README
- [ ] Follow your own Quick start in a fresh folder to prove it works (clone your repo somewhere else and run it)
- [ ] Commit and `git push`
- [ ] On GitHub, add a short description and topics (`python`, `pandas`, `accounting`, `reconciliation`)
- [ ] Pin the repo on your GitHub profile

**Done when:** someone else could run your project using only the README.

**Best practices in this step:**

- **Write for a stranger** — assume the reader has never seen your code or a bank rec.
- **Test your instructions** — a README that's never been followed usually has a missing step.
- **Lead with the business problem** — your accounting background is the differentiator, so say it up front.

## Best practices cheat sheet and what's next

| Practice | Learned in | One-line rule |
| --- | --- | --- |
| Virtual environment | Step 0 | One isolated environment per project; activate it every session |
| Commit often | Step 0 | Small commits, clear messages, commit after every working change |
| .gitignore | Step 0 | Generated files and environments never go in the repo |
| Reproducible data | Step 1 | Fixed random seed; know the expected answer before you build |
| Money as integer cents | Step 2 | Never do math on dollar floats |
| Validate at the edge | Step 2 | Check inputs where they enter; fail loudly with a clear message |
| Type hints and docstrings | Step 2 | Every function says what goes in, what comes out, and why it exists |
| Pure functions | Step 3 | Core logic takes data and returns data, with no file reads or prints inside |
| No magic numbers | Step 3 | Tunable values are named parameters |
| Separation of concerns | Step 4 | One job per file: load, match, report |
| Automated tests | Step 5 | One behavior per test; run them before every commit |
| Documentation for strangers | Step 6 | README tested by actually following it |

**V2 ideas, once V1 is done:**

- Many-to-one matching (one deposit covering several GL receipts)
- Fuzzy matching on description text
- A configurable date window and matching rules in a settings file
- A Streamlit web interface: upload two files, see the results
- Linting and formatting with `ruff`, plus GitHub Actions running your tests on every push
