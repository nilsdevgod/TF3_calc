"""TF3_calc — terminal calculator for Transport Fever 3 supply chains.

Enter the cargo a town demands (items per year), pick the recipe/producer
where chains branch, and get the transport rate to strive for on every line.
"""

import os
import sys
from datetime import datetime

from data import CARGO, INDUSTRY, producers_of, recipe_text
from chain import (
    AutoChooser,
    ChoiceError,
    compute_plan,
    format_plan,
    name_of,
    fmt_rate,
    DAYS_PER_YEAR,
)

REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")


def ask(prompt, default=None):
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"{prompt}{suffix}: ").strip()
    if not raw and default is not None:
        return default
    return raw


def ask_int(prompt, lo, hi, default=None):
    while True:
        raw = ask(prompt, default)
        try:
            value = int(raw)
        except ValueError:
            print(f"  Enter a number between {lo} and {hi}.")
            continue
        if lo <= value <= hi:
            return value
        print(f"  Enter a number between {lo} and {hi}.")


def ask_float(prompt, default=None):
    while True:
        raw = ask(prompt, default)
        try:
            value = float(raw.replace(",", "."))
        except ValueError:
            print("  Enter a number.")
            continue
        if value > 0:
            return value
        print("  Enter a number greater than 0.")


def ask_choice(prompt, options):
    """options: list of (label, value). Returns chosen value."""
    if len(options) == 1:
        return options[0][1]
    print(prompt)
    for i, (label, _value) in enumerate(options, 1):
        print(f"  {i}) {label}")
    idx = ask_int("Select", 1, len(options))
    return options[idx - 1][1]


def cargo_sorted_ids():
    order = {"End": 0, "Intermediate": 1, "Raw": 2, "Booster": 3}
    return sorted(CARGO, key=lambda c: (order[CARGO[c]["klass"]], CARGO[c]["name"]))


def pick_cargo(prompt):
    ids = cargo_sorted_ids()
    klass_short = {"End": "end", "Intermediate": "int", "Raw": "raw", "Booster": "boost"}
    print(prompt)
    for i, cargo_id in enumerate(ids, 1):
        meta = CARGO[cargo_id]
        print(f"  {i:2}) {meta['name']:<14} {klass_short[meta['klass']]:<5} {meta['category']}")
    idx = ask_int("Cargo number", 1, len(ids))
    return ids[idx - 1]


class InteractiveChooser:
    def choose_producer(self, cargo_id):
        options = producers_of(cargo_id)
        if not options:
            raise ChoiceError(f"No industry produces {CARGO[cargo_id]['name']}")
        if len(options) == 1:
            return options[0]
        return ask_choice(
            f"Which industry provides {CARGO[cargo_id]['name']}?",
            [(INDUSTRY[i]["name"], i) for i in options],
        )

    def choose_split(self, industry_id):
        ind = INDUSTRY[industry_id]
        if not ind.get("supports_split"):
            return [(0, 1.0)]
        labels = [r.get("label", f"Recipe {i + 1}") for i, r in enumerate(ind["recipes"])]
        choice = ask_choice(
            f"{ind['name']} recipe (inputs are alternatives):",
            [(labels[i], i) for i in range(len(labels))] + [("Mix (enter share)", "mix")],
        )
        if choice != "mix":
            return [(choice, 1.0)]
        share = ask_int(
            f"Share of output made with {labels[0]} in percent",
            0, 100, 50,
        ) / 100.0
        if share <= 0:
            return [(1, 1.0)]
        if share >= 1:
            return [(0, 1.0)]
        return [(0, share), (1, 1.0 - share)]


def prompt_demand():
    unit = ask("Rate unit: year or day? (y/d)", "y").lower()
    per_day = unit.startswith("d")
    cargo_id = pick_cargo("Deliver which cargo to the town?")
    if per_day:
        rate_day = ask_float(f"Demand for {CARGO[cargo_id]['name']} per day")
        rate = rate_day * DAYS_PER_YEAR
    else:
        rate = ask_float(f"Demand for {CARGO[cargo_id]['name']} per year")
    return cargo_id, rate


def save_report(plan):
    os.makedirs(REPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORT_DIR, f"plan_{stamp}.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(format_plan(plan))
        fh.write("\n")
    print(f"Saved to {path}")


def show_browse():
    print("\n--- Industries and recipes ---")
    for ind_id in sorted(INDUSTRY, key=lambda i: INDUSTRY[i]["name"]):
        print(f"  {INDUSTRY[ind_id]['name']:<18} {recipe_text(ind_id)}")
    print("\n--- Cargos ---")
    for cargo_id in cargo_sorted_ids():
        meta = CARGO[cargo_id]
        producers = ", ".join(INDUSTRY[p]["name"] for p in producers_of(cargo_id))
        print(f"  {meta['name']:<14} {meta['klass']:<12} {meta['category']:<8} by: {producers}")
    print()


def new_calculation():
    try:
        cargo_id, rate = prompt_demand()
        plan = compute_plan(cargo_id, rate, InteractiveChooser())
    except ChoiceError as exc:
        print(f"Cannot compute: {exc}")
        return
    except (KeyboardInterrupt, EOFError):
        print()
        return
    print()
    print(format_plan(plan))
    print()
    try:
        if ask("Save this plan to a report file? (y/n)", "n").lower().startswith("y"):
            save_report(plan)
    except (KeyboardInterrupt, EOFError):
        print()


def main():
    print("TF3_calc - Transport Fever 3 supply chain calculator")
    print("Rates are items per game year (365 game days).")
    while True:
        print()
        print("1) New calculation")
        print("2) Browse cargos and recipes")
        print("3) Quit")
        try:
            choice = ask("Select", "1")
        except (KeyboardInterrupt, EOFError):
            print()
            return
        if choice == "1":
            new_calculation()
        elif choice == "2":
            show_browse()
        elif choice in ("3", "q", "quit", "exit"):
            return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        sys.exit(0)