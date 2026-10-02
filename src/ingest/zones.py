"""Kerala flood zones definitions and metadata management."""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd


@dataclass(frozen=True)
class FloodZone:
    """Represents a monitored hydrological zone/district."""

    slug: str
    name: str
    district: str
    latitude: float
    longitude: float
    river_basin: str
    hydrological_type: str
    elevation_m: Optional[float] = None
    rationale: str = ""


# Deliberately selected representative coordinates for Kerala flood hazards
KERALA_ZONES: Dict[str, FloodZone] = {
    "ernakulam_aluva": FloodZone(
        slug="ernakulam_aluva",
        name="Aluva (Periyar Basin)",
        district="Ernakulam",
        latitude=10.1076,
        longitude=76.3516,
        river_basin="Periyar",
        hydrological_type="midland_riverine",
        rationale="Aluva town on Periyar River; key gauge station and 2018 flood epicenter.",
    ),
    "idukki_cheruthoni": FloodZone(
        slug="idukki_cheruthoni",
        name="Cheruthoni (Idukki Catchment)",
        district="Idukki",
        latitude=9.8494,
        longitude=76.9814,
        river_basin="Periyar Catchment",
        hydrological_type="high_relief_dam_catchment",
        rationale="Catchment downstream of Idukki Dam; high-slope runoff and gate release impact.",
    ),
    "wayanad_vythiri": FloodZone(
        slug="wayanad_vythiri",
        name="Vythiri / Meppadi (Kabini Catchment)",
        district="Wayanad",
        latitude=11.5500,
        longitude=76.0400,
        river_basin="Kabini",
        hydrological_type="highland_flash_flood",
        rationale="Extremely heavy monsoon rainfall belt; prone to rapid flash floods and debris flows.",
    ),
    "alappuzha_kuttanad": FloodZone(
        slug="alappuzha_kuttanad",
        name="Kuttanad (Vembanad Basin)",
        district="Alappuzha",
        latitude=9.4981,
        longitude=76.3388,
        river_basin="Pamba / Vembanad",
        hydrological_type="lowland_backwater_inundation",
        rationale="Below sea-level agricultural basin; prolonged drainage blockage and tidal waterlogging.",
    ),
    "pathanamthitta_kozhencherry": FloodZone(
        slug="pathanamthitta_kozhencherry",
        name="Kozhencherry (Pamba Basin)",
        district="Pathanamthitta",
        latitude=9.3364,
        longitude=76.6974,
        river_basin="Pamba",
        hydrological_type="midland_riverine",
        rationale="Pamba River gauge point; vulnerable to sudden water surge from upland cloudbursts.",
    ),
    "thrissur_chalakudy": FloodZone(
        slug="thrissur_chalakudy",
        name="Chalakudy (Chalakudy Basin)",
        district="Thrissur",
        latitude=10.3070,
        longitude=76.3330,
        river_basin="Chalakudy",
        hydrological_type="midland_riverine",
        rationale="Chalakudy River corridor; severely affected by Sholayar/Poringalkuthu dam discharges.",
    ),
    "kottayam_pala": FloodZone(
        slug="kottayam_pala",
        name="Pala (Meenachil Basin)",
        district="Kottayam",
        latitude=9.7100,
        longitude=76.6800,
        river_basin="Meenachil",
        hydrological_type="midland_riverine",
        rationale="Meenachil River valley; prone to flash inundation during heavy eastern hills precipitation.",
    ),
}


def get_all_zones() -> List[FloodZone]:
    """Return list of all configured flood zones."""
    return list(KERALA_ZONES.values())


def get_zone_by_slug(slug: str) -> Optional[FloodZone]:
    """Retrieve a flood zone by its slug identifier."""
    return KERALA_ZONES.get(slug)


def save_zones_to_csv(output_path: Path, zones_with_elevation: Optional[Dict[str, float]] = None) -> None:
    """Export zones with metadata and elevation to CSV."""
    records = []
    for zone in KERALA_ZONES.values():
        data = asdict(zone)
        if zones_with_elevation and zone.slug in zones_with_elevation:
            data["elevation_m"] = zones_with_elevation[zone.slug]
        records.append(data)

    df = pd.DataFrame(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
