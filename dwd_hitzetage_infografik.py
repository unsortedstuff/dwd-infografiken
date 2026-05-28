#!/usr/bin/env python3
"""Infografik: Heiße Tage (>=30°C) pro Zeitraum für eine Station im Stil einer Social-Media-Grafik."""
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from pathlib import Path
import numpy as np

CACHE_DIR = Path("dwd_cache")

def load_station(station_id):
    """Lade Daten einer Station (hist + recent)."""
    frames = []
    hist = CACHE_DIR / f"{station_id}_hist.parquet"
    recent = CACHE_DIR / f"{station_id}_recent.parquet"
    if hist.exists():
        frames.append(pd.read_parquet(hist))
    if recent.exists():
        frames.append(pd.read_parquet(recent))
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    df.columns = df.columns.str.strip()
    df['MESS_DATUM'] = pd.to_datetime(df['MESS_DATUM'], format='%Y%m%d', errors='coerce')
    df = df.drop_duplicates(subset=['MESS_DATUM'], keep='last')
    df['TXK'] = pd.to_numeric(df['TXK'], errors='coerce')
    df = df[df['TXK'] > -999]
    return df


def count_hot_days_per_year(df, threshold=30.0):
    """Zähle Tage >= threshold pro Jahr."""
    hot = df[df['TXK'] >= threshold].copy()
    hot['year'] = hot['MESS_DATUM'].dt.year
    return hot.groupby('year').size()


def create_infographic(station_name, station_ids, output_file, periods=None):
    """
    Erstelle Infografik für eine Station (oder kombinierte Stationen).

    station_ids: Liste von IDs (werden zusammengeführt für lückenlosen Datensatz)
    periods: Liste von (start, end, label) Tupeln
    """
    if periods is None:
        periods = [
            (1961, 1990, "1961–1990"),
            (1991, 2020, "1991–2020"),
            (2016, 2025, "Letzte\n10 Jahre"),
        ]

    # Daten laden und zusammenführen
    all_frames = []
    for sid in station_ids:
        df = load_station(sid)
        if df is not None:
            all_frames.append(df)

    if not all_frames:
        print(f"Keine Daten für {station_name} gefunden!")
        return

    combined = pd.concat(all_frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=['MESS_DATUM'], keep='last')

    hot_per_year = count_hot_days_per_year(combined)

    # Durchschnittliche heiße Tage pro Zeitraum berechnen
    values = []
    for start, end, label in periods:
        years_in_period = hot_per_year[(hot_per_year.index >= start) & (hot_per_year.index <= end)]
        n_years_data = len(years_in_period)
        n_years_total = end - start + 1
        # Mittelwert über alle Jahre im Zeitraum (auch Jahre mit 0 Tagen)
        all_years = range(start, end + 1)
        total_hot = sum(hot_per_year.get(y, 0) for y in all_years)
        avg = total_hot / n_years_total
        values.append(avg)
        print(f"  {label.replace(chr(10), ' ')}: {avg:.1f} heiße Tage/Jahr (Summe: {total_hot}, Jahre: {n_years_total})")

    # Klare, minimalistische Grafik
    fig, ax = plt.subplots(figsize=(5, 5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    # Titel
    ax.set_title(f"Heiße Tage (≥ 30 °C) in {station_name}\nDeutscher Wetterdienst",
                 fontsize=13, fontweight='bold', color='#222', pad=16)

    # Balken
    bar_colors = ['#4fc3f7', '#ffb74d', '#e53935']
    x_pos = [0, 1, 2]
    bar_width = 0.55

    bars = ax.bar(x_pos, values, width=bar_width, color=bar_colors[:len(values)],
                  edgecolor='none', zorder=3)

    # Werte über den Balken
    for i, (bar, val) in enumerate(zip(bars, values)):
        label = f"{val:.1f}".replace('.', ',')
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.02,
                label, ha='center', va='bottom', fontsize=14, fontweight='bold',
                color='#333')

    # X-Achse
    labels = [p[2] for p in periods]
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, fontsize=10, fontweight='bold', color='#333')
    ax.tick_params(axis='x', length=0, pad=8)

    # Y-Achse
    ax.set_ylim(0, max(values) * 1.25)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True, nbins=5))
    ax.set_ylabel('Ø Tage pro Jahr', fontsize=9, color='#555')
    ax.grid(axis='y', alpha=0.15, zorder=1)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#ccc')
    ax.spines['bottom'].set_color('#ccc')

    # Footer
    fig.text(0.14, 0.01, "Daten: DWD", fontsize=7, color='#aaa',
             transform=fig.transFigure)

    plt.tight_layout()
    plt.savefig(output_file, dpi=200, facecolor='white')
    plt.close()
    print(f"\nGespeichert: {output_file}")


def get_station_name(station_id):
    """Hole Stationsname aus DWD Stationsliste."""
    import urllib.request
    cache_file = CACHE_DIR / "station_names.csv"
    if not cache_file.exists():
        url = 'https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/historical/KL_Tageswerte_Beschreibung_Stationen.txt'
        data = urllib.request.urlopen(url).read().decode('latin-1')
        lines = data.strip().split('\n')[2:]  # Skip header
        rows = []
        for line in lines:
            if len(line) < 62:
                continue
            sid = line[0:5].strip()
            # Stationsname: Spalte 61-101 (feste Breite)
            name = line[61:101].strip()
            if sid and name:
                rows.append(f"{sid},{name}")
        cache_file.write_text('\n'.join(rows))
    # Lookup
    for line in cache_file.read_text().split('\n'):
        if line.startswith(station_id.lstrip('0') + ',') or line.startswith(station_id + ','):
            return line.split(',', 1)[1]
    return station_id


def generate_all_stations():
    """Generiere Infografiken für alle Stationen im Cache mit ausreichend Daten."""
    import os
    output_dir = Path("dwd_infografiken")
    output_dir.mkdir(exist_ok=True)

    hist_files = sorted(CACHE_DIR.glob("*_hist.parquet"))
    generated = 0
    skipped = 0

    for hf in hist_files:
        sid = hf.stem.replace("_hist", "")
        df = load_station(sid)
        if df is None:
            skipped += 1
            continue

        # Brauchen Daten von 1961-2025 (mindestens 50 Jahre abgedeckt)
        years = df['MESS_DATUM'].dt.year
        if years.min() > 1965 or years.max() < 2020:
            skipped += 1
            continue

        station_name = get_station_name(sid)
        output_file = output_dir / f"dwd_hitzetage_{sid}_{station_name.lower().replace(' ', '_').replace('/', '_')}.png"

        print(f"\n=== {station_name} ({sid}) ===")
        create_infographic(
            station_name=station_name,
            station_ids=[sid],
            output_file=str(output_file)
        )
        generated += 1

    print(f"\n{'='*50}")
    print(f"Fertig! {generated} Infografiken erstellt, {skipped} Stationen übersprungen.")
    print(f"Ausgabeordner: {output_dir}/")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--aurich':
        print("=== Aurich / Emden (Ostfriesland) ===")
        create_infographic(
            station_name="Aurich",
            station_ids=["00243", "05839"],
            output_file="dwd_hitzetage_aurich.png"
        )
    else:
        generate_all_stations()
