#!/usr/bin/env python3
"""Build station metadata for the static GitHub Pages map."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
STATION_FILE = ROOT / "dwd_cache" / "station_names.csv"
TARGET_FILE = ROOT / "assets" / "stations.json"


FILENAME_RE = re.compile(r"^dwd_hitzetage_(?P<station_id>\d{5})_.+\.png$")


def clean_state(value: str) -> str:
    return re.sub(r"\s+Frei$", "", value).strip()


def load_stations() -> dict[str, dict[str, str]]:
    with STATION_FILE.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        return {
            row["station_id"].zfill(5): {
                "name": row["name"].strip(),
                "state": clean_state(row["bundesland"]),
                "height": int(float(row["hoehe"])),
                "lat": float(row["breite"]),
                "lon": float(row["laenge"]),
            }
            for row in rows
        }


def main() -> None:
    station_lookup = load_stations()
    stations = []

    for image_path in sorted(OUTPUT_DIR.glob("dwd_hitzetage_*.png")):
        match = FILENAME_RE.match(image_path.name)
        if not match:
            continue

        station_id = match.group("station_id")
        station = station_lookup.get(station_id)
        if not station:
            print(f"Warnung: Keine Metadaten fuer {image_path.name}")
            continue

        stations.append(
            {
                "id": station_id,
                "name": station["name"],
                "state": station["state"],
                "height": station["height"],
                "lat": station["lat"],
                "lon": station["lon"],
                "image": f"output/{image_path.name}",
            }
        )

    TARGET_FILE.write_text(
        json.dumps(stations, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{len(stations)} Stationen nach {TARGET_FILE.relative_to(ROOT)} geschrieben.")


if __name__ == "__main__":
    main()
