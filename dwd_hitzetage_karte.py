#!/usr/bin/env python3
"""Extrahiert Tage >= 30 °C der letzten zwei Jahre je Station als Markdown
und erzeugt eine klickbare Leaflet-Karte mit den Werten pro Station."""
import csv
import json
import re
from pathlib import Path

import pandas as pd

CACHE_DIR = Path("dwd_cache")
OUTPUT_DIR = Path("output")
STATION_FILE = CACHE_DIR / "station_names.csv"
THRESHOLD = 30.0
END = pd.Timestamp("2026-05-27")
START = END - pd.DateOffset(years=2) + pd.Timedelta(days=1)


def clean_state(value: str) -> str:
    return re.sub(r"\s+Frei$", "", value).strip()


def load_station_meta():
    with STATION_FILE.open(newline="", encoding="utf-8") as fh:
        return {
            row["station_id"].zfill(5): {
                "name": row["name"].strip(),
                "state": clean_state(row["bundesland"]),
                "height": int(float(row["hoehe"])),
                "lat": float(row["breite"]),
                "lon": float(row["laenge"]),
            }
            for row in csv.DictReader(fh)
        }


def load_hot_days(station_id):
    """Tage >= THRESHOLD im Zeitfenster für eine Station."""
    frames = []
    for suffix in ("hist", "recent"):
        f = CACHE_DIR / f"{station_id}_{suffix}.parquet"
        if f.exists():
            frames.append(pd.read_parquet(f, columns=["MESS_DATUM", "TXK"]))
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    df["MESS_DATUM"] = pd.to_datetime(df["MESS_DATUM"], format="%Y%m%d", errors="coerce")
    df["TXK"] = pd.to_numeric(df["TXK"], errors="coerce")
    df = df.drop_duplicates(subset=["MESS_DATUM"], keep="last")
    df = df[(df["MESS_DATUM"] >= START) & (df["MESS_DATUM"] <= END) & (df["TXK"] >= THRESHOLD)]
    return df.sort_values("MESS_DATUM")[["MESS_DATUM", "TXK"]]


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    meta = load_station_meta()
    station_ids = sorted(p.stem.replace("_recent", "") for p in CACHE_DIR.glob("*_recent.parquet"))

    records = []  # (id, meta, DataFrame of hot days)
    for sid in station_ids:
        hot = load_hot_days(sid)
        if hot is None or hot.empty or sid not in meta:
            continue
        records.append((sid, meta[sid], hot))

    records.sort(key=lambda r: len(r[2]), reverse=True)

    write_markdown(records)
    write_map(records)


def write_markdown(records):
    out = OUTPUT_DIR / "hitzetage_letzte_2_jahre.md"
    total = sum(len(r[2]) for r in records)
    lines = [
        "# Hitzetage (≥ 30 °C) der letzten zwei Jahre",
        "",
        f"Zeitraum: **{START.date()}** bis **{END.date()}** · Datenquelle: DWD",
        "",
        f"{len(records)} Stationen mit insgesamt {total} Hitzetagen.",
        "",
    ]
    for sid, m, hot in records:
        lines.append(f"## {m['name']} ({sid}) — {m['state']}")
        lines.append("")
        lines.append(f"Höhe {m['height']} m · {m['lat']:.4f}, {m['lon']:.4f} · "
                     f"{len(hot)} Hitzetage")
        lines.append("")
        lines.append("| Datum | Max. Temperatur [°C] |")
        lines.append("|---|---|")
        for _, row in hot.iterrows():
            val = f"{row['TXK']:.1f}".replace(".", ",")
            lines.append(f"| {row['MESS_DATUM'].date()} | {val} |")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Markdown: {out} ({len(records)} Stationen, {total} Tage)")


def write_map(records):
    features = []
    for sid, m, hot in records:
        days = [
            {"d": row["MESS_DATUM"].strftime("%Y-%m-%d"), "t": round(float(row["TXK"]), 1)}
            for _, row in hot.iterrows()
        ]
        features.append({
            "id": sid,
            "name": m["name"],
            "state": m["state"],
            "height": m["height"],
            "lat": m["lat"],
            "lon": m["lon"],
            "count": len(days),
            "max": round(float(hot["TXK"].max()), 1),
            "days": days,
        })

    data_json = json.dumps(features, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("__DATA__", data_json) \
        .replace("__START__", str(START.date())) \
        .replace("__END__", str(END.date()))
    out = OUTPUT_DIR / "hitzetage_karte.html"
    out.write_text(html, encoding="utf-8")
    print(f"Karte: {out} ({len(features)} Stationen)")


HTML_TEMPLATE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hitzetage (≥ 30 °C) der letzten zwei Jahre</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">
<style>
  html, body { margin: 0; height: 100%; font-family: system-ui, sans-serif; }
  #map { height: 100%; width: 100%; }
  .legend { background: #fff; padding: 8px 10px; border-radius: 6px;
    box-shadow: 0 1px 4px rgba(0,0,0,.3); font-size: 13px; line-height: 1.5; }
  .legend i { display: inline-block; width: 14px; height: 14px; margin-right: 6px;
    border-radius: 50%; opacity: .85; }
  .popup h3 { margin: 0 0 4px; font-size: 15px; }
  .popup .meta { color: #555; font-size: 12px; margin-bottom: 6px; }
  .popup table { border-collapse: collapse; font-size: 12px; max-height: 220px;
    display: block; overflow-y: auto; }
  .popup td { padding: 1px 8px 1px 0; white-space: nowrap; }
  .popup td.t { text-align: right; font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
<script>
const DATA = __DATA__;
const map = L.map('map').setView([51.2, 10.4], 6);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 18,
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · '
    + 'Daten: <a href="https://opendata.dwd.de/">Deutscher Wetterdienst (DWD)</a> (GeoNutzV)'
}).addTo(map);

function color(c) {
  return c > 40 ? '#7f0000' : c > 25 ? '#d7301f' :
         c > 15 ? '#ef6548' : c > 7 ? '#fc8d59' : '#fdbb84';
}
function radius(c) { return Math.max(6, Math.min(22, 5 + Math.sqrt(c) * 2)); }

DATA.forEach(s => {
  const rows = s.days.map(d =>
    `<tr><td>${d.d}</td><td class="t">${d.t.toFixed(1).replace('.', ',')} °C</td></tr>`
  ).join('');
  const html = `<div class="popup"><h3>${s.name}</h3>
    <div class="meta">${s.state} · ${s.id} · ${s.height} m</div>
    <div class="meta"><strong>${s.count}</strong> Hitzetage · Max. ${s.max.toFixed(1).replace('.', ',')} °C</div>
    <table>${rows}</table></div>`;
  L.circleMarker([s.lat, s.lon], {
    radius: radius(s.count), color: '#7f0000', weight: 1,
    fillColor: color(s.count), fillOpacity: .85
  }).addTo(map).bindPopup(html, { maxWidth: 320 })
    .bindTooltip(`${s.name}: ${s.count}`, { direction: 'top' });
});

const legend = L.control({ position: 'bottomright' });
legend.onAdd = function () {
  const div = L.DomUtil.create('div', 'legend');
  div.innerHTML = '<strong>Hitzetage ≥ 30 °C</strong><br>'
    + '<span>__START__ – __END__</span><br>'
    + '<i style="background:#fdbb84"></i>1–7<br>'
    + '<i style="background:#fc8d59"></i>8–15<br>'
    + '<i style="background:#ef6548"></i>16–25<br>'
    + '<i style="background:#d7301f"></i>26–40<br>'
    + '<i style="background:#7f0000"></i>&gt;40';
  return div;
};
legend.addTo(map);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
