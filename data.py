"""Transport Fever 3 cargo and industry data.

Recipe ratios and cargo/industry facts are taken from the official wiki
(wiki.transportfever3.com, gamemanual:simulation:industriescargos).
Ratios are exact. Raw industries list per-year output ranges (min, typ, max)
which depend on their plots.
"""

CARGO = {
    "beverages": {"name": "Beverages", "category": "Goods", "klass": "End"},
    "books": {"name": "Books", "category": "Goods", "klass": "End"},
    "bricks": {"name": "Bricks", "category": "Goods", "klass": "End"},
    "canned_food": {"name": "Canned Food", "category": "Goods", "klass": "End"},
    "cement": {"name": "Cement", "category": "Bulk", "klass": "End"},
    "chemicals": {"name": "Chemicals", "category": "Liquid", "klass": "Intermediate"},
    "clay": {"name": "Clay", "category": "Bulk", "klass": "Raw"},
    "clothes": {"name": "Clothes", "category": "Goods", "klass": "End"},
    "coal": {"name": "Coal", "category": "Bulk", "klass": "Raw"},
    "crude_oil": {"name": "Crude Oil", "category": "Liquid", "klass": "Raw"},
    "dyes": {"name": "Dyes", "category": "Liquid", "klass": "Intermediate"},
    "fabric": {"name": "Fabric", "category": "Goods", "klass": "Intermediate"},
    "fertilizer": {"name": "Fertilizer", "category": "Bulk", "klass": "Booster"},
    "fish": {"name": "Fish", "category": "Goods", "klass": "Raw"},
    "fuel": {"name": "Fuel", "category": "Liquid", "klass": "End"},
    "furniture": {"name": "Furniture", "category": "Goods", "klass": "End"},
    "glass": {"name": "Glass", "category": "Goods", "klass": "Intermediate"},
    "grain": {"name": "Grain", "category": "Bulk", "klass": "Raw"},
    "iron_ore": {"name": "Iron Ore", "category": "Bulk", "klass": "Raw"},
    "logs": {"name": "Logs", "category": "Flatbed", "klass": "Raw"},
    "machines": {"name": "Machines", "category": "Flatbed", "klass": "Booster"},
    "meat": {"name": "Meat", "category": "Goods", "klass": "Raw"},
    "paper": {"name": "Paper", "category": "Goods", "klass": "Intermediate"},
    "planks": {"name": "Planks", "category": "Flatbed", "klass": "Intermediate"},
    "plastic": {"name": "Plastic", "category": "Goods", "klass": "Intermediate"},
    "rubber": {"name": "Rubber", "category": "Liquid", "klass": "Raw"},
    "sand": {"name": "Sand", "category": "Bulk", "klass": "Raw"},
    "sawdust": {"name": "Sawdust", "category": "Bulk", "klass": "Intermediate"},
    "sheet_metal": {"name": "Sheet Metal", "category": "Flatbed", "klass": "Intermediate"},
    "steel": {"name": "Steel", "category": "Flatbed", "klass": "Intermediate"},
    "stone": {"name": "Stone", "category": "Bulk", "klass": "Raw"},
    "tires": {"name": "Tires", "category": "Goods", "klass": "Intermediate"},
    "tools": {"name": "Tools", "category": "Goods", "klass": "Booster"},
    "vegetables": {"name": "Vegetables", "category": "Goods", "klass": "End"},
    "vehicles": {"name": "Vehicles", "category": "Flatbed", "klass": "End"},
    "wool": {"name": "Wool", "category": "Goods", "klass": "Raw"},
}

# kind "processor": recipes = list of {"inputs": {...}, "outputs": {...}, "label": str}
#   ratio quantities are per production cycle; multiple entries = alternative inputs.
#   supports_split = several recipes can run in parallel (user-chosen shares).
# kind "raw": outputs = {cargo: (min, typ, max)} items per year, scaled by plots.
# booster = cargo consumed to boost output (see wiki "Booster" section).

INDUSTRY = {
    "brewery": {
        "name": "Brewery",
        "kind": "processor",
        "recipes": [{"inputs": {"grain": 8, "glass": 3}, "outputs": {"beverages": 8}}],
        "booster": None,
    },
    "brick_works": {
        "name": "Brick Works",
        "kind": "processor",
        "recipes": [{"inputs": {"clay": 4}, "outputs": {"bricks": 4}}],
        "booster": None,
    },
    "canning_factory": {
        "name": "Canning Factory",
        "kind": "processor",
        "recipes": [
            {"inputs": {"fish": 2, "sheet_metal": 1}, "outputs": {"canned_food": 2}, "label": "Fish"},
            {"inputs": {"meat": 2, "sheet_metal": 1}, "outputs": {"canned_food": 2}, "label": "Meat"},
        ],
        "supports_split": True,
        "booster": None,
    },
    "cement_plant": {
        "name": "Cement Plant",
        "kind": "processor",
        "recipes": [{"inputs": {"stone": 4}, "outputs": {"cement": 2}}],
        "booster": None,
    },
    "chemical_plant": {
        "name": "Chemical Plant",
        "kind": "processor",
        "recipes": [{"inputs": {"chemicals": 6}, "outputs": {"dyes": 2, "plastic": 5}}],
        "booster": None,
    },
    "clay_pit": {
        "name": "Clay Pit",
        "kind": "raw",
        "outputs": {"clay": (1, 8, 16)},
        "booster": "tools",
    },
    "coal_mine": {
        "name": "Coal Mine",
        "kind": "raw",
        "outputs": {"coal": (1, 8, 16)},
        "booster": "tools",
    },
    "cotton_farm": {
        "name": "Cotton Farm",
        "kind": "raw",
        "outputs": {"wool": (1, 6, 12)},
        "booster": "fertilizer",
    },
    "crop_farm": {
        "name": "Crop Farm",
        "kind": "raw",
        "outputs": {"grain": (1, 12, 24), "vegetables": (1, 8, 16)},
        "booster": "fertilizer",
    },
    "fishing_grounds": {
        "name": "Fishing Grounds",
        "kind": "raw",
        "outputs": {"fish": (1, 6, 12)},
        "booster": "tools",
    },
    "furniture_factory": {
        "name": "Furniture Factory",
        "kind": "processor",
        "recipes": [{"inputs": {"planks": 4, "glass": 1}, "outputs": {"furniture": 2}}],
        "booster": "machines",
    },
    "glass_works": {
        "name": "Glass Works",
        "kind": "processor",
        "recipes": [{"inputs": {"sand": 4}, "outputs": {"glass": 2}}],
        "booster": None,
    },
    "iron_ore_mine": {
        "name": "Iron Ore Mine",
        "kind": "raw",
        "outputs": {"iron_ore": (1, 8, 16)},
        "booster": None,
    },
    "livestock_farm": {
        "name": "Livestock Farm",
        "kind": "processor",
        "recipes": [{"inputs": {"grain": 7}, "outputs": {"meat": 3, "wool": 4}}],
        "booster": "machines",
    },
    "logging_camp": {
        "name": "Logging Camp",
        "kind": "raw",
        "outputs": {"logs": (1, 4, 8)},
        "booster": None,
    },
    "machine_factory": {
        "name": "Machine Factory",
        "kind": "processor",
        "recipes": [{"inputs": {"steel": 7, "plastic": 4}, "outputs": {"machines": 7}}],
        "booster": None,
    },
    "oil_platform": {
        "name": "Oil Platform",
        "kind": "raw",
        "outputs": {"crude_oil": (1, 2, 4)},
        "booster": "tools",
    },
    "oil_refinery": {
        "name": "Oil Refinery",
        "kind": "processor",
        "recipes": [{
            "inputs": {"crude_oil": 4},
            "outputs": {"fuel": 2, "fertilizer": 1, "chemicals": 4},
        }],
        "booster": None,
    },
    "oil_well": {
        "name": "Oil Well",
        "kind": "raw",
        "outputs": {"crude_oil": (1, 3, 6)},
        "booster": "machines",
    },
    "paper_mill": {
        "name": "Paper Mill",
        "kind": "processor",
        "recipes": [{"inputs": {"sawdust": 4}, "outputs": {"paper": 2}}],
        "booster": None,
    },
    "printing_press": {
        "name": "Printing Press",
        "kind": "processor",
        "recipes": [{"inputs": {"paper": 4, "dyes": 2}, "outputs": {"books": 4}}],
        "booster": None,
    },
    "quarry": {
        "name": "Quarry",
        "kind": "raw",
        "outputs": {"stone": (1, 8, 16)},
        "booster": "tools",
    },
    "rubber_farm": {
        "name": "Rubber Farm",
        "kind": "raw",
        "outputs": {"rubber": (1, 16, 32)},
        "booster": "fertilizer",
    },
    "sand_excavator": {
        "name": "Sand Excavator",
        "kind": "raw",
        "outputs": {"sand": (1, 4, 8)},
        "booster": "machines",
    },
    "sand_pit": {
        "name": "Sand Pit",
        "kind": "raw",
        "outputs": {"sand": (1, 4, 8)},
        "booster": "tools",
    },
    "saw_mill": {
        "name": "Saw Mill",
        "kind": "processor",
        "recipes": [{"inputs": {"logs": 4}, "outputs": {"sawdust": 4, "planks": 8}}],
        "booster": None,
    },
    "steel_mill": {
        "name": "Steel Mill",
        "kind": "processor",
        "recipes": [{
            "inputs": {"iron_ore": 6, "coal": 6},
            "outputs": {"sheet_metal": 4, "steel": 3},
        }],
        "booster": None,
    },
    "textile_factory": {
        "name": "Textile Factory",
        "kind": "processor",
        "recipes": [{"inputs": {"fabric": 4, "dyes": 2}, "outputs": {"clothes": 3}}],
        "booster": None,
    },
    "tire_factory": {
        "name": "Tire Factory",
        "kind": "processor",
        "recipes": [{"inputs": {"rubber": 4}, "outputs": {"tires": 2}}],
        "booster": None,
    },
    "tool_factory": {
        "name": "Tool Factory",
        "kind": "processor",
        "recipes": [{"inputs": {"planks": 4, "plastic": 2}, "outputs": {"tools": 5}}],
        "booster": None,
    },
    "vehicle_factory": {
        "name": "Vehicle Factory",
        "kind": "processor",
        "recipes": [{
            "inputs": {"tires": 1, "sheet_metal": 4, "machines": 1},
            "outputs": {"vehicles": 1},
        }],
        "booster": None,
    },
    "weaving_mill": {
        "name": "Weaving Mill",
        "kind": "processor",
        "recipes": [{"inputs": {"wool": 4}, "outputs": {"fabric": 4}}],
        "booster": None,
    },
}


def producers_of(cargo_id):
    """Industries whose recipes/raw outputs can produce this cargo."""
    out = []
    for ind_id, ind in INDUSTRY.items():
        if ind["kind"] == "raw":
            if cargo_id in ind["outputs"]:
                out.append(ind_id)
        else:
            for recipe in ind["recipes"]:
                if cargo_id in recipe["outputs"]:
                    out.append(ind_id)
                    break
    return sorted(out)


def recipe_text(ind_id):
    ind = INDUSTRY[ind_id]
    if ind["kind"] == "raw":
        parts = []
        for cargo, (lo, _typ, hi) in sorted(ind["outputs"].items()):
            parts.append(f"{lo}-{hi} {CARGO[cargo]['name']}")
        text = " + ".join(parts) + " per year (plot-dependent)"
    else:
        texts = []
        for recipe in ind["recipes"]:
            left = " + ".join(f"{q} {CARGO[c]['name']}" for c, q in sorted(recipe["inputs"].items()))
            right = " + ".join(f"{q} {CARGO[c]['name']}" for c, q in sorted(recipe["outputs"].items()))
            texts.append(f"{left} -> {right}")
        text = " OR ".join(texts)
    if ind.get("booster"):
        text += f"   [booster: {CARGO[ind['booster']]['name']}]"
    return text
