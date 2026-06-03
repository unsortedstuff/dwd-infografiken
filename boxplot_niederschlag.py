#!/usr/bin/env python3
"""
Boxplot: Jahreszeitlicher Niederschlag Deutschland pro Jahrzehnt.

Berechnet den saisonalen Niederschlag (Sommer-/Winterhalbjahr) als Mittel
über alle DWD-Stationen und stellt ihn als Boxplot pro Jahrzehnt dar.
Eine Linie verbindet die Mediane der Jahrzehnte.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

CACHE_DIR = Path("dwd_cache")
OUTPUT_DIR = Path("output")


def load_all_stations():
    """Alle gecachten Stationsdaten laden und zusammenführen."""
    frames = []
    for f in sorted(CACHE_DIR.glob("*_hist.parquet")):
        station_id = f.stem.split("_")[0]
        df = pd.read_parquet(f)
        # Recent-Daten dazuladen falls vorhanden
        recent_file = CACHE_DIR / f"{station_id}_recent.parquet"
        if recent_file.exists():
            df_recent = pd.read_parquet(recent_file)
            df = pd.concat([df, df_recent]).drop_duplicates(subset=['MESS_DATUM'])
        df['station'] = station_id
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def compute_seasonal_precip(df):
    """Saisonalen Niederschlag pro Station und Jahr berechnen.

    Sommerhalbjahr: April-September
    Winterhalbjahr: Oktober-März (dem Folgejahr zugeordnet, z.B. Okt 1960 - Mär 1961 = Winter 1960/61)
    """
    # Ungültige Werte filtern
    df = df[df['RSK'] >= 0].copy()
    df['year'] = df['MESS_DATUM'].dt.year
    df['month'] = df['MESS_DATUM'].dt.month

    # Sommerhalbjahr: Apr-Sep
    sommer = df[df['month'].between(4, 9)].copy()
    sommer_sum = sommer.groupby(['station', 'year'])['RSK'].sum().reset_index()
    sommer_sum.rename(columns={'RSK': 'precip_mm'}, inplace=True)
    sommer_sum['saison'] = 'Sommerhalbjahr'

    # Winterhalbjahr: Okt-Mär
    # Okt-Dez gehört zum Winter des gleichen Jahres, Jan-Mär zum Vorjahr
    winter = df[df['month'].isin([10, 11, 12, 1, 2, 3])].copy()
    winter['winter_year'] = np.where(winter['month'] >= 10, winter['year'], winter['year'] - 1)
    winter_sum = winter.groupby(['station', 'winter_year'])['RSK'].sum().reset_index()
    winter_sum.rename(columns={'winter_year': 'year', 'RSK': 'precip_mm'}, inplace=True)
    winter_sum['saison'] = 'Winterhalbjahr'

    return pd.concat([sommer_sum, winter_sum], ignore_index=True)


def germany_mean_per_year(seasonal):
    """Mittelwert über alle Stationen pro Jahr und Saison."""
    # Nur Jahre mit mindestens 20 Stationen
    counts = seasonal.groupby(['saison', 'year'])['station'].nunique().reset_index()
    counts.rename(columns={'station': 'n_stations'}, inplace=True)
    seasonal = seasonal.merge(counts, on=['saison', 'year'])
    seasonal = seasonal[seasonal['n_stations'] >= 20]

    mean = seasonal.groupby(['saison', 'year'])['precip_mm'].mean().reset_index()
    return mean


def assign_decade(df):
    """Jahrzehnt-Spalte hinzufügen."""
    df['decade'] = (df['year'] // 10) * 10
    return df


def plot_boxplots(data):
    """Boxplot pro Jahrzehnt mit Medianlinie für beide Halbjahre."""
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    for ax, saison, color in zip(axes, ['Sommerhalbjahr', 'Winterhalbjahr'], ['#e74c3c', '#3498db']):
        subset = data[data['saison'] == saison].copy()
        decades = sorted(subset['decade'].unique())

        # Boxplot-Daten vorbereiten
        box_data = [subset[subset['decade'] == d]['precip_mm'].values for d in decades]
        labels = [f"{d}er" for d in decades]

        bp = ax.boxplot(box_data, labels=labels, patch_artist=True,
                        medianprops=dict(color='black', linewidth=2),
                        boxprops=dict(facecolor=color, alpha=0.4),
                        whiskerprops=dict(color=color),
                        capprops=dict(color=color),
                        flierprops=dict(markerfacecolor=color, marker='o', alpha=0.5, markersize=4))

        # Medianlinie verbinden
        medians = [np.median(d) for d in box_data]
        positions = range(1, len(decades) + 1)
        ax.plot(positions, medians, 'o-', color='black', linewidth=2, markersize=6, zorder=5,
                label='Median pro Jahrzehnt')

        # Gesamtmedian als horizontale Linie
        all_values = np.concatenate(box_data)
        overall_median = np.median(all_values)
        ax.axhline(overall_median, color='black', linewidth=0.8, linestyle='--', alpha=0.6,
                   label=f'Gesamtmedian ({overall_median:.0f} mm)')

        ax.set_ylabel('Niederschlag [mm]')
        ax.set_title(saison, fontsize=14, fontweight='bold', color=color)
        ax.legend(loc='upper left')
        ax.grid(axis='y', alpha=0.3)

    fig.suptitle('Jahreszeitlicher Niederschlag Deutschland — Boxplot pro Jahrzehnt\n'
                 'Datenquelle: DWD (Mittel über alle Stationen)', fontsize=13)
    plt.tight_layout()

    OUTPUT_DIR.mkdir(exist_ok=True)
    outfile = OUTPUT_DIR / "boxplot_niederschlag_jahrzehnte.png"
    plt.savefig(outfile, dpi=150, bbox_inches='tight')
    print(f"Gespeichert: {outfile}")
    plt.close()


def main():
    print("Lade alle Stationsdaten...")
    df = load_all_stations()
    print(f"  {df['station'].nunique()} Stationen, {len(df)} Tageswerte geladen.")

    print("Berechne saisonalen Niederschlag...")
    seasonal = compute_seasonal_precip(df)

    print("Berechne Deutschlandmittel pro Jahr...")
    mean = germany_mean_per_year(seasonal)
    mean = assign_decade(mean)

    # Unvollständige Jahre entfernen (laufendes Jahr hat nicht alle Monate)
    mean = mean[mean['year'] <= 2025]

    # Nur vollständige Jahrzehnte (mind. 5 Jahre)
    decade_counts = mean.groupby(['saison', 'decade'])['year'].nunique().reset_index()
    valid = decade_counts[decade_counts['year'] >= 5][['saison', 'decade']]
    mean = mean.merge(valid, on=['saison', 'decade'])

    print(f"  Jahrzehnte: {sorted(mean['decade'].unique())}")
    print("Erstelle Boxplot...")
    plot_boxplots(mean)


if __name__ == "__main__":
    main()
