"""Chain expansion engine for TF3_calc.

Given a town demand (cargo + items per year) and the user's recipe/producer
choices, computes the transport rate for every line in the supply chain,
plus surplus byproduct rates.

All rates are items per game year (365 game days).
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field

from data import CARGO, INDUSTRY, producers_of

EPS = 1e-9
DAYS_PER_YEAR = 365


@dataclass
class Flow:
    src: str          # industry id or "town"
    dst: str          # industry id or "town"
    cargo: str        # cargo id
    rate: float       # items per year


@dataclass
class Surplus:
    src: str
    cargo: str
    rate: float


@dataclass
class Note:
    text: str


@dataclass
class Plan:
    target_cargo: str
    target_rate: float
    lines: list = field(default_factory=list)
    surpluses: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    cycles: dict = field(default_factory=dict)   # ind -> cycles per year (processors)
    producers: dict = field(default_factory=dict)  # cargo -> [(ind, share)]


class ChoiceError(Exception):
    pass


@dataclass
class RateAnchor:
    ind_id: str       # industry whose one-plant rate is given
    rate: float       # items per year from one plant of ind_id


class AutoChooser:
    """Non-interactive chooser for tests: preset producer and split picks."""

    def __init__(self, producer_picks=None, split_picks=None):
        self.producer_picks = producer_picks or {}
        self.split_picks = split_picks or {}

    def choose_producer(self, cargo_id):
        options = producers_of(cargo_id)
        if not options:
            raise ChoiceError(f"No industry produces {CARGO[cargo_id]['name']}")
        if len(options) == 1:
            return options[0]
        pick = self.producer_picks.get(cargo_id)
        if pick is None:
            raise ChoiceError(f"Producer choice needed for {CARGO[cargo_id]['name']}: {options}")
        return pick

    def choose_split(self, industry_id):
        ind = INDUSTRY[industry_id]
        if not ind.get("supports_split"):
            return [(0, 1.0)]
        pick = self.split_picks.get(industry_id)
        if pick is None:
            raise ChoiceError(f"Recipe choice needed for {ind['name']}")
        return pick


def _in_rate(ind, mix, cargo):
    return sum(share * ind["recipes"][i]["inputs"].get(cargo, 0) for i, share in mix)


def _out_rate(ind, mix, cargo):
    return sum(share * ind["recipes"][i]["outputs"].get(cargo, 0) for i, share in mix)


def _all_outputs(ind, mix):
    outs = set()
    for i, share in mix:
        if share > 0:
            outs.update(ind["recipes"][i]["outputs"])
    return outs


def _all_inputs(ind, mix):
    ins = set()
    for i, share in mix:
        if share > 0:
            ins.update(ind["recipes"][i]["inputs"])
    return ins


def anchor_input(ind, recipe_index):
    """The input cargo that distinguishes this recipe from the alternatives."""
    other = set()
    for j, recipe in enumerate(ind["recipes"]):
        if j != recipe_index:
            other.update(recipe["inputs"])
    distinct = sorted(c for c in ind["recipes"][recipe_index]["inputs"] if c not in other)
    if len(distinct) != 1:
        raise ChoiceError("Cannot derive a rate anchor for this recipe")
    return distinct[0]


def mix_from_anchor(ind, anchor_index, anchor_cargo, anchor_rate, output_demand):
    """Mix shares from a one-plant rate anchor.

    The anchor recipe consumes anchor_rate items/year of anchor_cargo and the
    remaining recipes cover the rest of output_demand (items/year of the
    industry's output). Every recipe must yield the same single output per
    cycle (the Canning Factory does).
    """
    recipes = ind["recipes"]
    if not 0 <= anchor_index < len(recipes):
        raise ChoiceError("Unknown recipe index")
    if output_demand <= 0:
        raise ChoiceError("Demand must be greater than zero")
    if anchor_rate < 0:
        raise ChoiceError("Plant rate must not be negative")
    anchor = recipes[anchor_index]
    in_qty = anchor["inputs"].get(anchor_cargo, 0)
    if in_qty <= 0:
        raise ChoiceError(f"{CARGO[anchor_cargo]['name']} is not an input of that recipe")
    if len(anchor["outputs"]) != 1:
        raise ChoiceError("Rate-anchored mixes need recipes with a single output")
    out_cargo, out_qty = next(iter(anchor["outputs"].items()))
    for recipe in recipes:
        if recipe["outputs"] != {out_cargo: out_qty}:
            raise ChoiceError("Rate-anchored mixes need every recipe to yield the same output")
    share = anchor_rate * out_qty / (in_qty * output_demand)
    share = min(1.0, max(0.0, share))
    shares = [0.0] * len(recipes)
    shares[anchor_index] = share
    others = [i for i in range(len(recipes)) if i != anchor_index]
    if others:
        rest = (1.0 - share) / len(others)
        for i in others:
            shares[i] = rest
    else:
        shares[anchor_index] = 1.0
    return [(i, s) for i, s in enumerate(shares) if s > EPS]


def source_inds(cargo_id, choice):
    """Every industry that may supply this cargo under a producer choice."""
    if isinstance(choice, RateAnchor):
        options = producers_of(cargo_id)
        if choice.ind_id not in options:
            raise ChoiceError(
                f"{INDUSTRY[choice.ind_id]['name']} does not produce {CARGO[cargo_id]['name']}"
            )
        return options
    ids = [choice] if isinstance(choice, str) else [ind_id for ind_id, _share in choice]
    for ind_id in ids:
        if ind_id not in producers_of(cargo_id):
            raise ChoiceError(
                f"{INDUSTRY[ind_id]['name']} does not produce {CARGO[cargo_id]['name']}"
            )
    return ids


def resolve_sources(cargo_id, choice, demand_rate):
    """Concrete [(ind_id, share)] (sums to 1) for a producer choice.

    A RateAnchor supplies at most one plant's rate and the other producers
    share the remainder. Explicit share lists are normalised to sum to 1.
    """
    ids = source_inds(cargo_id, choice)
    if isinstance(choice, str):
        return [(choice, 1.0)]
    if isinstance(choice, RateAnchor):
        others = [i for i in ids if i != choice.ind_id]
        if not others:
            return [(choice.ind_id, 1.0)]
        if demand_rate <= 0:
            raise ChoiceError("Demand must be greater than zero")
        if choice.rate < 0:
            raise ChoiceError("Plant rate must not be negative")
        share = min(1.0, choice.rate / demand_rate)
        if share >= 1.0:
            return [(choice.ind_id, 1.0)]
        if share <= EPS:
            return [(i, 1.0 / len(others)) for i in others]
        rest = (1.0 - share) / len(others)
        return [(choice.ind_id, share)] + [(i, rest) for i in others]
    pairs = [(ind_id, float(weight)) for ind_id, weight in choice]
    total = sum(weight for _, weight in pairs)
    if total <= EPS:
        raise ChoiceError("Producer shares must sum to a positive value")
    return [(ind_id, weight / total) for ind_id, weight in pairs]


def compute_plan(target_cargo, target_rate, chooser):
    if target_rate <= 0:
        raise ChoiceError("Demand must be greater than zero")

    # ---- discovery: walk from the target through chosen producers ----
    producers = {}
    mixes = {}
    discovered = set()
    industries = set()
    queue = deque([target_cargo])
    while queue:
        cargo = queue.popleft()
        if cargo in discovered:
            continue
        discovered.add(cargo)
        choice = chooser.choose_producer(cargo)
        producers[cargo] = choice
        for ind_id in source_inds(cargo, choice):
            industries.add(ind_id)
            ind = INDUSTRY[ind_id]
            if ind["kind"] == "raw":
                continue
            if ind_id not in mixes:
                mixes[ind_id] = chooser.choose_split(ind_id)
            for inc in _all_inputs(ind, mixes[ind_id]):
                queue.append(inc)

    # ---- topological order: consumers before the producers of their inputs ----
    indegree = defaultdict(int)
    dependents = defaultdict(set)   # consumer -> producers it unblocks
    for ind_id in industries:
        indegree.setdefault(ind_id, 0)
    for ind_id, mix in mixes.items():
        ind = INDUSTRY[ind_id]
        for inc in _all_inputs(ind, mix):
            for prod in source_inds(inc, producers[inc]):
                if prod == ind_id:
                    continue
                if prod not in dependents[ind_id]:
                    dependents[ind_id].add(prod)
                    indegree[prod] += 1

    ready = sorted(i for i in industries if indegree[i] == 0)
    order = []
    while ready:
        ind_id = ready.pop(0)
        order.append(ind_id)
        for consumer in sorted(dependents[ind_id]):
            indegree[consumer] -= 1
            if indegree[consumer] == 0:
                ready.append(consumer)
                ready.sort()
    if len(order) != len(industries):
        raise ChoiceError("Cycle detected in production chain")

    # ---- scale industries, aggregate demands, build flows ----
    demand = defaultdict(float)
    demand[target_cargo] = target_rate
    resolved = {}                      # cargo -> [(ind_id, share)]
    assigned = defaultdict(float)      # (ind_id, cargo) -> items/year it supplies
    requests = [("town", target_cargo, target_rate)]   # (consumer, cargo, rate)
    surpluses = []
    notes = []
    cycles = {}

    def sources_of(cargo):
        # consumers are ordered before the producers of their inputs, so the
        # demand is final the first time a cargo's sources are resolved
        if cargo not in resolved:
            resolved[cargo] = resolve_sources(cargo, producers[cargo], demand[cargo])
            for ind_id, share in resolved[cargo]:
                assigned[(ind_id, cargo)] = demand[cargo] * share
        return resolved[cargo]

    def portion_of(ind_id, cargo):
        if demand[cargo] <= EPS:
            return 0.0
        sources_of(cargo)
        return assigned.get((ind_id, cargo), 0.0)

    for ind_id in order:
        ind = INDUSTRY[ind_id]
        if ind["kind"] == "raw":
            continue
        mix = mixes[ind_id]

        # enough cycles to cover this industry's share of every demanded output
        # (coupled outputs net out; zero-share branches stay idle)
        total_cycles = 0.0
        for out_cargo in _all_outputs(ind, mix):
            rate_per_cycle = _out_rate(ind, mix, out_cargo)
            if rate_per_cycle <= 0:
                continue
            portion = portion_of(ind_id, out_cargo)
            if portion > EPS:
                total_cycles = max(total_cycles, portion / rate_per_cycle)
        cycles[ind_id] = total_cycles

        for out_cargo in sorted(_all_outputs(ind, mix)):
            produced = _out_rate(ind, mix, out_cargo) * total_cycles
            leftover = produced - portion_of(ind_id, out_cargo)
            if leftover > EPS:
                surpluses.append(Surplus(ind_id, out_cargo, leftover))

        for inc in sorted(_all_inputs(ind, mix)):
            rate = _in_rate(ind, mix, inc) * total_cycles
            if rate <= EPS:
                continue
            requests.append((ind_id, inc, rate))
            demand[inc] += rate

    # one line per source: a split supply shows up as several lines
    lines = []
    for consumer, cargo, rate in requests:
        for ind_id, share in sources_of(cargo):
            if share <= EPS:
                continue
            lines.append(Flow(ind_id, consumer, cargo, rate * share))

    # raw industries: report undemanded side outputs (plot-dependent ranges)
    for ind_id in sorted(industries):
        ind = INDUSTRY[ind_id]
        if ind["kind"] != "raw":
            continue
        if not any(portion_of(ind_id, out_cargo) > EPS for out_cargo in ind["outputs"]):
            continue
        for out_cargo, (lo, _typ, hi) in sorted(ind["outputs"].items()):
            if demand[out_cargo] <= EPS:
                notes.append(Note(
                    f"{ind['name']} also yields {CARGO[out_cargo]['name']} "
                    f"at {lo}-{hi}/year (plot-dependent)"
                ))

    # sort lines: town delivery first, then by cargo name
    lines.sort(key=lambda f: (f.dst != "town", CARGO[f.cargo]["name"], f.src))
    surpluses.sort(key=lambda s: CARGO[s.cargo]["name"])

    return Plan(
        target_cargo=target_cargo,
        target_rate=target_rate,
        lines=lines,
        surpluses=surpluses,
        notes=notes,
        cycles=cycles,
        producers=dict(resolved),
    )


def name_of(node_id):
    return "Town" if node_id == "town" else INDUSTRY[node_id]["name"]


def fmt_rate(n):
    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return f"{n:.1f}"


def fmt_day(n):
    return f"{n / DAYS_PER_YEAR:.2f}"


def format_plan(plan):
    out = []
    cargo_name = CARGO[plan.target_cargo]["name"]
    out.append(f"=== Plan: {fmt_rate(plan.target_rate)} {cargo_name}/year to the town ===")
    out.append("")
    out.append("Lines to ship (rates to strive for):")
    width_src = max(len(name_of(f.src)) for f in plan.lines)
    width_dst = max(len(name_of(f.dst)) for f in plan.lines)
    width_cargo = max(len(CARGO[f.cargo]["name"]) for f in plan.lines)
    for f in plan.lines:
        out.append(
            f"  {name_of(f.src):<{width_src}} -> {name_of(f.dst):<{width_dst}}  "
            f"{CARGO[f.cargo]['name']:<{width_cargo}}  "
            f"{fmt_rate(f.rate):>7} /year  ({fmt_day(f.rate)} /day)"
        )
    if plan.surpluses:
        out.append("")
        out.append("Surplus (find a consumer or it is destroyed past the stock limit):")
        for s in plan.surpluses:
            out.append(
                f"  {name_of(s.src)}: {fmt_rate(s.rate)} {CARGO[s.cargo]['name']}/year "
                f"({fmt_day(s.rate)} /day)"
            )
    for note in plan.notes:
        out.append("")
        out.append(f"Note: {note.text}")
    return "\n".join(out)


if __name__ == "__main__":
    # quick self-checks against hand calculations
    p = compute_plan("meat", 100, AutoChooser())
    rates = {(f.src, f.dst, f.cargo): f.rate for f in p.lines}
    assert rates[("livestock_farm", "town", "meat")] == 100
    assert abs(rates[("crop_farm", "livestock_farm", "grain")] - 700 / 3) < 1e-9
    assert abs(p.surpluses[0].rate - 400 / 3) < 1e-9
    assert p.surpluses[0].cargo == "wool"

    p = compute_plan("canned_food", 150, AutoChooser(split_picks={"canning_factory": [(0, 1.0)]}))
    rates = {(f.src, f.dst, f.cargo): f.rate for f in p.lines}
    assert rates[("fishing_grounds", "canning_factory", "fish")] == 150
    assert rates[("steel_mill", "canning_factory", "sheet_metal")] == 75
    assert rates[("iron_ore_mine", "steel_mill", "iron_ore")] == 112.5
    assert rates[("coal_mine", "steel_mill", "coal")] == 112.5
    surplus = {s.cargo: s.rate for s in p.surpluses}
    assert surplus["steel"] == 56.25

    p = compute_plan(
        "canned_food", 100,
        AutoChooser(split_picks={"canning_factory": [(0, 0.5), (1, 0.5)]}),
    )
    rates = {(f.src, f.dst, f.cargo): f.rate for f in p.lines}
    assert rates[("fishing_grounds", "canning_factory", "fish")] == 50
    assert rates[("livestock_farm", "canning_factory", "meat")] == 50
    assert rates[("steel_mill", "canning_factory", "sheet_metal")] == 50

    p = compute_plan("vehicles", 10, AutoChooser(producer_picks={"crude_oil": "oil_well"}))
    rates = {(f.src, f.dst, f.cargo): f.rate for f in p.lines}
    assert rates[("vehicle_factory", "town", "vehicles")] == 10
    assert rates[("steel_mill", "vehicle_factory", "sheet_metal")] == 40
    assert rates[("machine_factory", "vehicle_factory", "machines")] == 10
    assert rates[("tire_factory", "vehicle_factory", "tires")] == 10
    assert rates[("steel_mill", "machine_factory", "steel")] == 10
    assert rates[("chemical_plant", "machine_factory", "plastic")] == 40 / 7
    assert rates[("rubber_farm", "tire_factory", "rubber")] == 20
    assert rates[("iron_ore_mine", "steel_mill", "iron_ore")] == 60
    assert rates[("coal_mine", "steel_mill", "coal")] == 60
    assert rates[("oil_refinery", "chemical_plant", "chemicals")] == 240 / 35
    assert rates[("oil_well", "oil_refinery", "crude_oil")] == 240 / 35
    surplus = defaultdict(float)
    for s in p.surpluses:
        surplus[s.cargo] += s.rate
    assert abs(surplus["steel"] - 20) < 1e-9

    # rate-anchored recipe mix: one Fishing Grounds supplies 6 fish of 100 canned food
    canning = INDUSTRY["canning_factory"]
    assert anchor_input(canning, 0) == "fish"
    assert anchor_input(canning, 1) == "meat"
    mix = mix_from_anchor(canning, 0, "fish", 6, 100)
    assert [i for i, _ in mix] == [0, 1]
    assert abs(dict(mix)[0] - 0.06) < 1e-9
    assert abs(dict(mix)[1] - 0.94) < 1e-9
    mix = mix_from_anchor(canning, 1, "meat", 25, 100)
    assert abs(dict(mix)[0] - 0.75) < 1e-9
    assert abs(dict(mix)[1] - 0.25) < 1e-9
    assert mix_from_anchor(canning, 0, "fish", 150, 100) == [(0, 1.0)]
    assert mix_from_anchor(canning, 1, "meat", 100, 100) == [(1, 1.0)]
    assert mix_from_anchor(canning, 0, "fish", 0, 100) == [(1, 1.0)]

    p = compute_plan(
        "canned_food", 100,
        AutoChooser(split_picks={"canning_factory": mix_from_anchor(canning, 0, "fish", 6, 100)}),
    )
    rates = {(f.src, f.dst, f.cargo): f.rate for f in p.lines}
    assert rates[("fishing_grounds", "canning_factory", "fish")] == 6
    assert rates[("livestock_farm", "canning_factory", "meat")] == 94
    assert rates[("steel_mill", "canning_factory", "sheet_metal")] == 50
    assert rates[("iron_ore_mine", "steel_mill", "iron_ore")] == 75
    assert rates[("coal_mine", "steel_mill", "coal")] == 75
    surplus = {s.cargo: s.rate for s in p.surpluses}
    assert surplus["steel"] == 37.5

    # rate-anchored producer splits
    shares = resolve_sources("crude_oil", RateAnchor("oil_platform", 4.0), 20)
    assert len(shares) == 2
    assert abs(shares[0][1] - 0.2) < 1e-9
    assert abs(shares[1][1] - 0.8) < 1e-9
    assert resolve_sources("crude_oil", RateAnchor("oil_platform", 40.0), 20) == [("oil_platform", 1.0)]
    assert resolve_sources("crude_oil", "oil_well", 20) == [("oil_well", 1.0)]
    assert resolve_sources("crude_oil", [("oil_well", 1), ("oil_platform", 3)], 20) == [
        ("oil_well", 0.25), ("oil_platform", 0.75),
    ]

    p = compute_plan(
        "vehicles", 10,
        AutoChooser(producer_picks={"crude_oil": RateAnchor("oil_platform", 4.0)}),
    )
    rates = {(f.src, f.dst, f.cargo): f.rate for f in p.lines}
    assert rates[("oil_platform", "oil_refinery", "crude_oil")] == 4
    assert abs(rates[("oil_well", "oil_refinery", "crude_oil")] - 20 / 7) < 1e-9

    # Wool from one Livestock Farm at most: the rest comes from Cotton Farms
    p = compute_plan(
        "clothes", 20,
        AutoChooser(producer_picks={
            "wool": RateAnchor("livestock_farm", 4.0),
            "crude_oil": "oil_well",
        }),
    )
    rates = {(f.src, f.dst, f.cargo): f.rate for f in p.lines}
    assert rates[("livestock_farm", "weaving_mill", "wool")] == 4
    assert abs(rates[("cotton_farm", "weaving_mill", "wool")] - 68 / 3) < 1e-9
    assert rates[("crop_farm", "livestock_farm", "grain")] == 7
    surplus = {s.cargo: s.rate for s in p.surpluses}
    assert surplus["meat"] == 3

    print("chain.py self-checks passed")