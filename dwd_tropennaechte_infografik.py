#!/usr/bin/env python3
"""Infografik: Tropennächte (TNK >= 20 °C) pro Zeitraum für eine Station im Stil einer Social-Media-Grafik."""
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

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
    df['TNK'] = pd.to_numeric(df['TNK'], errors='coerce')
    df = df[df['TNK'] > -999]
    return df


def count_tropical_nights_per_year(df, threshold=20.0):
    """Zähle Nächte mit Tiefsttemperatur >= threshold pro Jahr."""
    trop = df[df['TNK'] >= threshold].copy()
    trop['year'] = trop['MESS_DATUM'].dt.year
    return trop.groupby('year').size()


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

    trop_per_year = count_tropical_nights_per_year(combined)

    values = []
    for start, end, label in periods:
        n_years_total = end - start + 1
        all_years = range(start, end + 1)
        total_trop = sum(trop_per_year.get(y, 0) for y in all_years)
        avg = total_trop / n_years_total
        values.append(avg)
        print(f"  {label.replace(chr(10), ' ')}: {avg:.1f} Tropennächte/Jahr "
              f"(Summe: {total_trop}, Jahre: {n_years_total})")

    fig, ax = plt.subplots(figsize=(5, 5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    ax.set_title(f"Tropennächte (≥ 20 °C) in {station_name}\nDeutscher Wetterdienst",
                 fontsize=13, fontweight='bold', color='#222', pad=16)

    bar_colors = ['#9fa8da', '#7e57c2', '#4527a0']
    x_pos = [0, 1, 2]
    bar_width = 0.55

    bars = ax.bar(x_pos, values, width=bar_width, color=bar_colors[:len(values)],
                  edgecolor='none', zorder=3)

    y_top = max(values) if max(values) > 0 else 1
    for bar, val in zip(bars, values):
        label = f"{val:.1f}".replace('.', ',')
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + y_top*0.02,
                label, ha='center', va='bottom', fontsize=14, fontweight='bold',
                color='#333')

    labels = [p[2] for p in periods]
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, fontsize=10, fontweight='bold', color='#333')
    ax.tick_params(axis='x', length=0, pad=8)

    ax.set_ylim(0, y_top * 1.25)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True, nbins=5))
    ax.set_ylabel('Ø Nächte pro Jahr', fontsize=9, color='#555')
    ax.grid(axis='y', alpha=0.15, zorder=1)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#ccc')
    ax.spines['bottom'].set_color('#ccc')

    fig.text(0.14, 0.01, "Daten: DWD", fontsize=7, color='#aaa',
             transform=fig.transFigure)

    plt.tight_layout()
    plt.savefig(output_file, dpi=200, facecolor='white')
    plt.close()
    print(f"\nGespeichert: {output_file}")


def generate_all_stations():
    """Generiere Infografiken für alle Stationen im Cache mit ausreichend Daten."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    station_list_file = CACHE_DIR / "station_names.csv"
    if station_list_file.exists():
        station_df = pd.read_csv(station_list_file, dtype={'station_id': str})
        station_df['station_id'] = station_df['station_id'].str.zfill(5)
        station_df['bundesland'] = station_df['bundesland'].str.strip().str.replace(r'\s+Frei$', '', regex=True)
        station_df['name'] = station_df['name'].str.strip()
    else:
        station_df = pd.DataFrame()

    hist_files = sorted(CACHE_DIR.glob("*_hist.parquet"))
    generated = 0
    skipped = 0

    for hf in hist_files:
        sid = hf.stem.replace("_hist", "")
        df = load_station(sid)
        if df is None:
            skipped += 1
            continue

        years = df['MESS_DATUM'].dt.year
        if years.min() > 1965 or years.max() < 2020:
            skipped += 1
            continue

        station_name = sid
        bundesland = ""
        if not station_df.empty:
            row = station_df[station_df['station_id'] == sid]
            if not row.empty:
                station_name = row.iloc[0]['name']
                bundesland = row.iloc[0]['bundesland']
        name_clean = station_name.lower().replace(' ', '_').replace('/', '_').replace(',', '').replace('"', '')
        bl_clean = bundesland.lower().replace(' ', '-').replace('ü', 'ue').replace('ö', 'oe').replace('ä', 'ae') if bundesland else ''
        output_file = output_dir / f"dwd_tropennaechte_{sid}_{name_clean}_{bl_clean}.png"

        print(f"\n=== {station_name} ({sid}) ===")
        create_infographic(
            station_name=station_name,
            station_ids=[sid],
            output_file=str(output_file)
        )
        generated += 1

    print(f"\n{'='*50}")
    print(f"Fertig! {generated} Infografiken erstellt, {skipped} Stationen übersprungen.")
    print(f"Ausgabeordner: {output_dir.resolve()}/")


if __name__ == '__main__':
    generate_all_stations()
