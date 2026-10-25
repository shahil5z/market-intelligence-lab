"""Seeded generators for the SYNTHETIC dimensions that the public dataset does not contain.

Everything produced here is invented for demonstration and is labelled `synthetic` in the
data dictionary: campaign metadata, product pack size and region market_type.
"""

import numpy as np
import pandas as pd
from common import SEED

# Country -> region group. This is a simple geographic grouping (derived, not synthetic).
REGION_GROUPS = {
    "United Kingdom": "United Kingdom",
    "EIRE": "Ireland & Channel Is.",
    "Channel Islands": "Ireland & Channel Is.",
    "Germany": "Western Europe",
    "France": "Western Europe",
    "Netherlands": "Western Europe",
    "Belgium": "Western Europe",
    "Switzerland": "Western Europe",
    "Austria": "Western Europe",
    "Luxembourg": "Western Europe",
    "Spain": "Southern Europe",
    "Portugal": "Southern Europe",
    "Italy": "Southern Europe",
    "Greece": "Southern Europe",
    "Malta": "Southern Europe",
    "Cyprus": "Southern Europe",
    "Sweden": "Northern Europe",
    "Denmark": "Northern Europe",
    "Norway": "Northern Europe",
    "Finland": "Northern Europe",
    "Iceland": "Northern Europe",
    "Poland": "Northern Europe",
    "Lithuania": "Northern Europe",
    "Czech Republic": "Northern Europe",
}
REST = "Rest of World"

# Category is assigned by keyword rules on the real product description (derived).
CATEGORY_RULES = [
    ("Christmas & Seasonal", ["CHRISTMAS", "XMAS", "EASTER", "ADVENT", "SNOWFLAKE", "REINDEER", "SANTA"]),
    ("Bags & Storage", ["BAG", "BOX", "TIN", "JAR", "BASKET", "STORAGE", "CASE"]),
    ("Kitchen & Dining", ["MUG", "CUP", "PLATE", "BOWL", "TEA", "CAKE", "KITCHEN", "LUNCH", "BAKING", "NAPKIN", "SPOON"]),
    ("Lighting & Candles", ["LIGHT", "CANDLE", "LANTERN", "T-LIGHT", "HOLDER"]),
    ("Home Decor", ["HEART", "SIGN", "FRAME", "CUSHION", "CLOCK", "MIRROR", "DECORATION", "HANGING", "DOORSTOP", "VINTAGE"]),
    ("Stationery & Gifts", ["CARD", "WRAP", "PAPER", "NOTEBOOK", "PEN", "GIFT", "STICKER", "RIBBON", "TAPE"]),
    ("Toys & Kids", ["TOY", "DOLL", "GAME", "CHILDREN", "PLAYHOUSE", "SPACEBOY", "DOLLY", "KIDS"]),
    ("Garden & Outdoor", ["GARDEN", "BIRD", "PICNIC", "PARASOL", "UMBRELLA"]),
]
OTHER = "Other"

PACK_SIZES = [1, 2, 3, 6, 12, 24]

# Public UK bank holidays 2009-12 to 2011-12 (transcribed from the gov.uk calendar).
UK_BANK_HOLIDAYS = [
    "2009-12-25",
    "2009-12-28",
    "2010-01-01",
    "2010-04-02",
    "2010-04-05",
    "2010-05-03",
    "2010-05-31",
    "2010-08-30",
    "2010-12-27",
    "2010-12-28",
    "2011-01-03",
    "2011-04-22",
    "2011-04-25",
    "2011-04-29",
    "2011-05-02",
    "2011-05-30",
    "2011-08-29",
    "2011-12-26",
    "2011-12-27",
]


def assign_category(description: str) -> str:
    text = (description or "").upper()
    for category, words in CATEGORY_RULES:
        if any(w in text for w in words):
            return category
    return OTHER


def region_table(countries: list[str]) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    for i, country in enumerate(sorted(countries), start=1):
        group = REGION_GROUPS.get(country, REST)
        market_type = "Domestic" if country == "United Kingdom" else str(rng.choice(["Mature", "Developing"]))
        rows.append({"region_id": i, "country": country, "region_group": group, "market_type": market_type})
    return pd.DataFrame(rows)


def pack_sizes(n: int) -> np.ndarray:
    rng = np.random.default_rng(SEED + 1)
    return rng.choice(PACK_SIZES, size=n, p=[0.35, 0.15, 0.1, 0.2, 0.15, 0.05])


def campaign_table(start: pd.Timestamp, end: pd.Timestamp, categories: list[str], region_groups: list[str]) -> pd.DataFrame:
    """12 synthetic campaigns spread across the data period. Each targets one region group and
    one category. Windows are random but never overlap the first 60 days (needed for a baseline)."""
    rng = np.random.default_rng(SEED + 2)
    channels = ["Email", "Social Media", "Search Ads", "Catalogue", "Trade Partner"]
    types = ["Seasonal", "Price Promotion", "Product Launch", "Awareness"]
    rows = []
    usable_start = start + pd.Timedelta(days=60)
    span_days = (end - usable_start).days - 40
    for i in range(1, 13):
        cstart = usable_start + pd.Timedelta(days=int(rng.integers(0, span_days)))
        duration = int(rng.integers(14, 36))
        rows.append(
            {
                "campaign_id": i,
                "campaign_name": f"Campaign {i:02d}",
                "channel": str(rng.choice(channels)),
                "campaign_type": str(rng.choice(types)),
                "start_date": cstart.normalize(),
                "end_date": (cstart + pd.Timedelta(days=duration - 1)).normalize(),
                "budget": float(rng.integers(20, 160) * 100),
                "target_region_group": str(rng.choice(region_groups, p=_weights(region_groups, REGION_WEIGHTS))),
                "target_category": str(rng.choice([c for c in categories if c != OTHER])),
            }
        )
    out = pd.DataFrame(rows).sort_values("start_date").reset_index(drop=True)
    out["campaign_id"] = np.arange(1, len(out) + 1)  # ids follow chronological order
    out["campaign_name"] = [f"Campaign {i:02d}" for i in out["campaign_id"]]
    return out


# Campaign targets are drawn more often for high-volume region groups so that each synthetic
# campaign touches enough real transactions to analyse.
REGION_WEIGHTS = {"United Kingdom": 6, "Western Europe": 3, "Ireland & Channel Is.": 2}


def _weights(values: list[str], table: dict) -> list[float]:
    w = np.array([table.get(v, 1) for v in values], dtype=float)
    return list(w / w.sum())
