# DWD Hitzetage-Infografiken

Automatische Erstellung von Infografiken zur Entwicklung heißer Tage (≥ 30 °C) an deutschen Wetterstationen. Die Grafiken vergleichen drei Zeiträume und zeigen den Anstieg der durchschnittlichen Hitzetage pro Jahr:

- **1961–1990** (alte Klimareferenzperiode)
- **1991–2020** (aktuelle Klimareferenzperiode)
- **Letzte 10 Jahre** (2016–2025)

Die Daten stammen vom [Deutschen Wetterdienst (DWD)](https://opendata.dwd.de/), der seine Klimadaten als Open Data bereitstellt.

## Beispiel

![Beispiel-Infografik](dwd_hitzetage_01420_frankfurt_main.png)

## Voraussetzungen

- Python 3.10+
- Internetverbindung (für den erstmaligen Download der DWD-Daten)

## Installation

```bash
git clone --recurse-submodules https://github.com/unsortedstuff/dwd-infografiken.git
cd dwd-infografiken

python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

Falls bereits geklont ohne Submodules:

```bash
git submodule update --init --recursive
```

## Daten herunterladen

Der Downloader ist als Git-Submodul eingebunden ([dwd-downloader](https://github.com/unsortedstuff/dwd-downloader)). Er lädt die Stationsdaten vom DWD Open Data Server und speichert sie als Parquet-Dateien im Verzeichnis `dwd_cache/`.

```bash
# Alle Stationen mit Daten ab 1950 herunterladen
python dwd-downloader/dwd_download.py

# Stationen mit Daten ab 1900
python dwd-downloader/dwd_download.py --seit 1900

# Nur eine bestimmte Station
python dwd-downloader/dwd_download.py --station 00433

# Cache überschreiben (erneuter Download)
python dwd-downloader/dwd_download.py --force
```

Pro Station werden zwei Parquet-Dateien angelegt:

```
dwd_cache/<stations_id>_hist.parquet    # Historische Daten
dwd_cache/<stations_id>_recent.parquet  # Aktuelle Daten
```

Die Dateien enthalten die täglichen Klimadaten (KL-Tageswerte) mit den Spalten `MESS_DATUM` (Datum) und `TXK` (Tagesmaximum der Lufttemperatur in °C).

Datenquelle: https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/

## Verwendung

### Alle Stationen generieren

Erstellt Infografiken für alle Stationen im Cache, die ausreichend lange Messreihen haben (Daten ab spätestens 1965, mindestens bis 2020):

```bash
python dwd_hitzetage_infografik.py
```

Die Grafiken werden im Verzeichnis `dwd_infografiken/` (Unterordner des aktuellen Verzeichnisses) abgelegt.

### Einzelne Station (Beispiel Aurich)

```bash
python dwd_hitzetage_infografik.py --aurich
```

## Ausgabe

Pro Station wird eine PNG-Datei (1000×1000 px bei 200 dpi) erzeugt:

```
dwd_hitzetage_<stations_id>_<stationsname>.png
```

Die Grafiken sind als Social-Media-taugliche Infografiken gestaltet mit:
- Drei farblich codierten Balken (blau → orange → rot)
- Durchschnittliche Hitzetage pro Jahr je Zeitraum
- Quellenangabe (DWD)

## Projektstruktur

```
dwd-infografiken/
├── dwd-downloader/               # Submodul: DWD-Daten herunterladen
├── dwd_hitzetage_infografik.py   # Infografiken erzeugen
├── requirements.txt              # Python-Abhängigkeiten
├── .gitignore
├── README.md
├── dwd_cache/                    # Stationsdaten (nicht im Repo)
└── dwd_infografiken/             # Erzeugte Infografiken
```

## Lizenz

Die Klimadaten des DWD stehen unter der [GeoNutzV](https://www.gesetze-im-internet.de/geonutzv/) (freie Nutzung mit Quellenangabe).

## Datenquelle

Deutscher Wetterdienst (DWD), Klimadaten Deutschland, Tageswerte der Stationen:
https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/daily/kl/
