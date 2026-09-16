# coding: utf-8
"""Regenera los .parquet de "data/" a partir de los .csv.

Cada parquet es una copia exacta del CSV tal como lo lee `app/core.py`
(`skiprows=[0]`, `names=Nombres`): mismas filas, mismas columnas, mismo orden y
sin aplicar `dropna()`, que sigue haciéndose al cargar. Así el parquet sustituye
al CSV sin cambiar ni un valor.

Uso:
    python tools/csv_a_parquet.py
"""

import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

ARCHIVOS = ["SB2951", "SB2953", "SB2954", "SB2955"]
COMPRESION = "zstd"

# El mismo encabezado que usa app/core.py
Nombres = ['Fecha', 'Flujo Gas', 'Flujo Aire', 'Producción Vapor', 'Temp. Vapor',
           'Oxigeno', 'T Aire al Cal', 'Poder', 'IGV']


def convertir(nombre):
    csv = DATA_DIR / f"{nombre}.csv"
    parquet = DATA_DIR / f"{nombre}.parquet"

    original = pd.read_csv(csv, skiprows=[0], names=Nombres)
    original.to_parquet(parquet, engine="pyarrow", compression=COMPRESION, index=False)

    # Round-trip: el parquet debe devolver exactamente el mismo DataFrame.
    pd.testing.assert_frame_equal(pd.read_parquet(parquet), original)

    mb_csv = csv.stat().st_size / 1e6
    mb_pq = parquet.stat().st_size / 1e6
    print(f"{nombre}: {len(original):>7} filas | "
          f"csv {mb_csv:6.1f} MB -> parquet {mb_pq:5.1f} MB "
          f"({mb_pq / mb_csv:.0%}) | round-trip OK")
    return mb_csv, mb_pq


def main():
    if not DATA_DIR.is_dir():
        sys.exit(f"No existe {DATA_DIR}")

    total_csv = total_pq = 0.0
    for nombre in ARCHIVOS:
        csv, pq = convertir(nombre)
        total_csv += csv
        total_pq += pq

    print(f"\nTotal: {total_csv:.0f} MB -> {total_pq:.0f} MB "
          f"(ahorro {total_csv - total_pq:.0f} MB)")


if __name__ == "__main__":
    main()
