#!/usr/bin/env python3
"""Infografik: Jährliche Höchsttemperaturen Deutschland in Kelvin, Referenz 0 K (absoluter Nullpunkt)."""
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from pathlib import Path

from dwd_hoechsttemperaturen_infografik import yearly_max_germany

KELVIN = 273.15


def create_infographic(output_file, start_year=1950, end_year=2025,
                       meme_image=None):
    """Erstelle Infografik der Höchsttemperaturen in Kelvin ab 0 K."""
    yearly = yearly_max_germany(start_year, end_year) + KELVIN
    if yearly.empty:
        print("Keine Daten gefunden!")
        return

    years = yearly.index.to_numpy()
    values = yearly.to_numpy()
    print(f"Bereich: {values.min():.1f}–{values.max():.1f} K")

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    ax.set_title("Jährliche Höchsttemperaturen Deutschland",
                 fontsize=20, color='#222', pad=28)
    ax.text(0.5, 1.015, "- Datenquelle: DWD · Referenz 0 K -",
            transform=ax.transAxes, ha='center', va='bottom',
            fontsize=12, color='#444')

    ax.bar(years, values, width=0.8, color='#ed7d31',
           edgecolor='#c55a11', linewidth=0.4, zorder=3)

    # 5-Jahres-Mittel (zentriert)
    rolling = yearly.rolling(window=5, center=True, min_periods=5).mean()
    ax.plot(rolling.index.to_numpy(), rolling.to_numpy(), color='#1f3864',
            linewidth=2.5, zorder=4, label='5-Jahres-Mittel')
    ax.legend(loc='lower right', fontsize=11, frameon=False)

    ax.set_ylim(0, 320)
    ax.set_xlim(start_year - 1, end_year + 1)
    ax.set_ylabel('Höchste lokale Temperatur [K]', fontsize=13, color='#333')
    ax.tick_params(axis='both', labelsize=11, color='#ccc')
    ax.grid(axis='both', alpha=0.25, color='#cccccc', linewidth=0.6, zorder=1)
    for spine in ax.spines.values():
        spine.set_color('#bbbbbb')

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
        output_file=str(output_dir / "dwd_hoechsttemperaturen_kelvin_deutschland.png"),
        meme_image=meme,
    )
