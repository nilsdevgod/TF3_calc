# TF3_calc

Supply chain calculator for **Transport Fever 3**. Enter what a town demands, pick the recipe where chains fork, and get the exact transport rate to strive for on every line.

## Usage

**Browser (recommended):** open `index.html` — no server or install needed.

**Terminal:** `python3 main.py` (standard library only).

Workflow:

1. Enter the town's demand (e.g. `100` Meat per year, or per day).
2. Pick the cargo to deliver.
3. Answer the branch questions where chains fork (e.g. Canned Food from fish, meat, or a mix).
4. Get the rate to ship on every line, grouped by tier:

| Tier | What it carries | Example (clothes chain) |
|---|---|---|
| **Primary** | Raw materials from the map | Wool, Crude Oil |
| **Secondary** | Intermediate goods between factories | Fabric, Dyes, Chemicals |
| **Third** | End product delivered to the town | Clothes |

Coupled byproducts (e.g. Steel Mill's steel, Livestock Farm's wool) are netted against demand in the chain and shown as **surplus** when nobody consumes them — find them a consumer or they get destroyed past the industry's stock limit.

## Example

`100 Meat/year` to the town:

| Line | Rate |
|---|---|
| Livestock Farm → Town (Meat) | 100 /year (0.27 /day) |
| Crop Farm → Livestock Farm (Grain) | 233.3 /year (0.64 /day) |
| *Surplus: Livestock Farm (Wool)* | *133.3 /year* |

## Numbers

- All rates are **items per game year** (365 game days), matching the game's industry window and cargo layer.
- Recipe ratios are taken from the [official Transport Fever 3 wiki](https://wiki.transportfever3.com/doku.php?id=gamemanual:simulation:industriescargos) (32 industries, 36 cargos) and are exact.
- The line rates are **targets to size your lines for**. What your line manager later shows is the actual throughput of your vehicles — it matches the target once the line is sized right.

## Files

| File | Purpose |
|---|---|
| `index.html` | Self-contained browser version (data + engine included) |
| `data.py` | Cargo and industry data |
| `chain.py` | Calculation engine (`python3 chain.py` runs self-checks) |
| `main.py` | Terminal UI |

Unofficial fan tool. Game data © Urban Games / Paradox Interactive.