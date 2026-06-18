#!/usr/bin/env python3
"""Infografik: Jährliche Höchsttemperaturen in Deutschland (Maximum aller Stationen pro Jahr)."""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from pathlib import Path

CACHE_DIR = Path("dwd_cache")


def load_station(station_id):
    """Lade Daten einer Station (hist + recent), nur Datum + Tagesmaximum."""
    frames = []
    for suffix in ("hist", "recent"):
        f = CACHE_DIR / f"{station_id}_{suffix}.parquet"
        if f.exists():
            frames.append(pd.read_parquet(f, columns=['MESS_DATUM', 'TXK']))
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    df.columns = df.columns.str.strip()
    df['MESS_DATUM'] = pd.to_datetime(df['MESS_DATUM'], format='%Y%m%d', errors='coerce')
    df['TXK'] = pd.to_numeric(df['TXK'], errors='coerce')
    df = df[df['TXK'] > -999]
    return df[['MESS_DATUM', 'TXK']]


def yearly_max_germany(start_year, end_year):
    """Höchste je Jahr in ganz Deutschland gemessene Temperatur (Maximum aller Stationen)."""
    hist_files = sorted(CACHE_DIR.glob("*_hist.parquet"))
    station_ids = [hf.stem.replace("_hist", "") for hf in hist_files]

    max_by_year = {}
    for sid in station_ids:
        df = load_station(sid)
        if df is None or df.empty:
            continue
        years = df['MESS_DATUM'].dt.year
        per_year = df.groupby(years)['TXK'].max()
        for y, v in per_year.items():
            if start_year <= y <= end_year:
                if y not in max_by_year or v > max_by_year[y]:
                    max_by_year[y] = v

    s = pd.Series(max_by_year).sort_index()
    return s


def create_infographic(output_file, start_year=1950, end_year=2025,
                        meme_image=None):
    """Erstelle Infografik der jährlichen Höchsttemperaturen in Deutschland."""
    yearly = yearly_max_germany(start_year, end_year)
    if yearly.empty:
        print("Keine Daten gefunden!")
        return

    years = yearly.index.to_numpy()
    values = yearly.to_numpy()
    print(f"Jahre: {years.min()}–{years.max()}, "
          f"Höchstwert: {values.max():.1f} °C ({years[values.argmax()]})")

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    # Titel + Datenquelle
    ax.set_title("Jährliche Höchsttemperaturen Deutschland",
                 fontsize=20, color='#222', pad=28)
    ax.text(0.5, 1.015, "- Datenquelle: DWD -", transform=ax.transAxes,
            ha='center', va='bottom', fontsize=12, color='#444')

    # Balken
    ax.bar(years, values, width=0.8, color='#ed7d31',
           edgecolor='#c55a11', linewidth=0.4, zorder=3)

    # 5-Jahres-Mittel (zentriert)
    rolling = yearly.rolling(window=5, center=True, min_periods=5).mean()
    ax.plot(rolling.index.to_numpy(), rolling.to_numpy(), color='#1f3864',
            linewidth=2.5, zorder=4, label='5-Jahres-Mittel')
    ax.legend(loc='lower right', fontsize=11, frameon=False)

    # Achsen
    ax.set_ylim(0, 50)
    ax.set_xlim(start_year - 1, end_year + 1)
    ax.set_ylabel('Höchste lokale Temperatur [°C]', fontsize=13, color='#333')
    ax.set_yticks(range(0, 51, 10))
    ax.tick_params(axis='both', labelsize=11, color='#ccc')
    ax.grid(axis='both', alpha=0.25, color='#cccccc', linewidth=0.6, zorder=1)
    for spine in ax.spines.values():
        spine.set_color('#bbbbbb')

    # Optionales Meme-Overlay
    if meme_image and Path(meme_image).exists():
        img = mpimg.imread(meme_image)
        oi = OffsetImage(img, zoom=0.45)
        ab = AnnotationBbox(oi, (0.55, 0.42), xycoords='axes fraction',
                            frameon=False, zorder=5)
        ax.add_artist(ab)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, facecolor='white')
    plt.close()
    print(f"Gespeichert: {output_file}")


if __name__ == '__main__':
    import sys
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    meme = sys.argv[1] if len(sys.argv) > 1 else None
    create_infographic(
        output_file=str(output_dir / "dwd_hoechsttemperaturen_deutschland.png"),
        meme_image=meme,
    )
