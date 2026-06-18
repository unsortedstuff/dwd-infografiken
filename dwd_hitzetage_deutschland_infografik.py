#!/usr/bin/env python3
"""Infografik: Hitzetage (>=30°C) pro Jahr, deutschlandweiter Durchschnitt pro Station."""
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


def hot_days_per_year_germany(start_year, end_year, threshold=30.0):
    """Durchschnittliche Hitzetage (>= threshold) pro Station und Jahr, deutschlandweit.

    Zählt je Station die Tage >= threshold pro Jahr und mittelt über alle
    Stationen mit Daten in dem Jahr. So bleibt der Wert vergleichbar, obwohl
    die Anzahl aktiver Stationen über die Jahrzehnte schwankt.
    """
    hist_files = sorted(CACHE_DIR.glob("*_hist.parquet"))
    station_ids = [hf.stem.replace("_hist", "") for hf in hist_files]

    hot_sum = {}    # Jahr -> Summe der Hitzetage über alle Stationen
    station_cnt = {}  # Jahr -> Anzahl Stationen mit Daten
    for sid in station_ids:
        df = load_station(sid)
        if df is None or df.empty:
            continue
        df = df[(df['MESS_DATUM'].dt.year >= start_year) &
                (df['MESS_DATUM'].dt.year <= end_year)]
        if df.empty:
            continue
        years = df['MESS_DATUM'].dt.year
        # Stationen mit ausreichend Messtagen pro Jahr zählen
        days_per_year = df.groupby(years).size()
        hot = df[df['TXK'] >= threshold]
        hot_per_year = hot.groupby(hot['MESS_DATUM'].dt.year).size()
        for y, n_days in days_per_year.items():
            if n_days < 300:  # unvollständige Jahre überspringen
                continue
            hot_sum[y] = hot_sum.get(y, 0) + int(hot_per_year.get(y, 0))
            station_cnt[y] = station_cnt.get(y, 0) + 1

    rows = {y: hot_sum[y] / station_cnt[y] for y in hot_sum if station_cnt[y] > 0}
    return pd.Series(rows).sort_index()


def create_infographic(output_file, start_year=1950, end_year=2025,
                       threshold=30.0, meme_image=None):
    """Erstelle Infografik der deutschlandweiten Hitzetage pro Jahr."""
    yearly = hot_days_per_year_germany(start_year, end_year, threshold)
    if yearly.empty:
        print("Keine Daten gefunden!")
        return

    years = yearly.index.to_numpy()
    values = yearly.to_numpy()
    print(f"Jahre: {years.min()}–{years.max()}, "
          f"Höchstwert: {values.max():.1f} Tage ({years[values.argmax()]})")

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    ax.set_title("Hitzetage (≥ 30 °C) pro Jahr in Deutschland",
                 fontsize=20, color='#222', pad=28)
    ax.text(0.5, 1.015, "- Datenquelle: DWD -", transform=ax.transAxes,
            ha='center', va='bottom', fontsize=12, color='#444')

    ax.bar(years, values, width=0.8, color='#ed7d31',
           edgecolor='#c55a11', linewidth=0.4, zorder=3)

    # 5-Jahres-Mittel (zentriert)
    rolling = yearly.rolling(window=5, center=True, min_periods=5).mean()
    ax.plot(rolling.index.to_numpy(), rolling.to_numpy(), color='#1f3864',
            linewidth=2.5, zorder=4, label='5-Jahres-Mittel')
    ax.legend(loc='upper left', fontsize=11, frameon=False)

    ax.set_ylim(0, max(values) * 1.15)
    ax.set_xlim(start_year - 1, end_year + 1)
    ax.set_ylabel('Ø Hitzetage pro Station', fontsize=13, color='#333')
    ax.tick_params(axis='both', labelsize=11, color='#ccc')
    ax.grid(axis='both', alpha=0.25, color='#cccccc', linewidth=0.6, zorder=1)
    for spine in ax.spines.values():
        spine.set_color('#bbbbbb')

    if meme_image and Path(meme_image).exists():
        img = mpimg.imread(meme_image)
        oi = OffsetImage(img, zoom=0.45)
        ab = AnnotationBbox(oi, (0.3, 0.65), xycoords='axes fraction',
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
        output_file=str(output_dir / "dwd_hitzetage_deutschland.png"),
        meme_image=meme,
    )
