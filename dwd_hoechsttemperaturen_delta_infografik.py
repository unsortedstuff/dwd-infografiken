#!/usr/bin/env python3
"""Infografik: Jährliche Höchsttemperaturen Deutschland als Abweichung zum Referenzmittel 1950–1970."""
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from pathlib import Path

from dwd_hoechsttemperaturen_infografik import yearly_max_germany

REF_START, REF_END = 1950, 1970


def create_infographic(output_file, start_year=1950, end_year=2025,
                       meme_image=None):
    """Erstelle Infografik der Höchsttemperatur-Abweichung zum Referenzmittel."""
    yearly = yearly_max_germany(start_year, end_year)
    if yearly.empty:
        print("Keine Daten gefunden!")
        return

    ref = yearly[(yearly.index >= REF_START) & (yearly.index <= REF_END)].mean()
    delta = yearly - ref

    years = delta.index.to_numpy()
    values = delta.to_numpy()
    print(f"Referenzmittel {REF_START}–{REF_END}: {ref:.1f} °C")
    print(f"Größte Abweichung: {values.max():+.1f} °C ({years[values.argmax()]})")

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    ax.set_title("Höchsttemperaturen Deutschland – Abweichung vom Mittel",
                 fontsize=20, color='#222', pad=28)
    ax.text(0.5, 1.015, f"- Datenquelle: DWD · Referenz {REF_START}–{REF_END} -",
            transform=ax.transAxes, ha='center', va='bottom',
            fontsize=12, color='#444')

    colors = ['#ed7d31' if v >= 0 else '#5b9bd5' for v in values]
    edge = ['#c55a11' if v >= 0 else '#2e75b6' for v in values]
    ax.bar(years, values, width=0.8, color=colors,
           edgecolor=edge, linewidth=0.4, zorder=3)

    # 5-Jahres-Mittel (zentriert)
    rolling = delta.rolling(window=5, center=True, min_periods=5).mean()
    ax.plot(rolling.index.to_numpy(), rolling.to_numpy(), color='#1f3864',
            linewidth=2.5, zorder=4, label='5-Jahres-Mittel')

    # Nulllinie (Referenzniveau)
    ax.axhline(0, color='#555', linewidth=1.0, zorder=2)
    ax.legend(loc='lower right', fontsize=11, frameon=False)

    ax.set_xlim(start_year - 1, end_year + 1)
    ax.set_ylabel('Abweichung vom Referenzmittel [°C]', fontsize=13, color='#333')
    ax.tick_params(axis='both', labelsize=11, color='#ccc')
    ax.grid(axis='both', alpha=0.25, color='#cccccc', linewidth=0.6, zorder=1)
    for spine in ax.spines.values():
        spine.set_color('#bbbbbb')

    if meme_image and Path(meme_image).exists():
        img = mpimg.imread(meme_image)
        oi = OffsetImage(img, zoom=0.45)
        ab = AnnotationBbox(oi, (0.3, 0.75), xycoords='axes fraction',
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
        output_file=str(output_dir / "dwd_hoechsttemperaturen_delta_deutschland.png"),
        meme_image=meme,
    )
