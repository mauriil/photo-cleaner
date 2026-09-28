#!/usr/bin/env python3
"""Clasifica fotos como explicitas / no explicitas y las organiza por fecha de captura."""

import sys
import shutil
from pathlib import Path
from datetime import datetime

import pillow_heif
pillow_heif.register_heif_opener()

from PIL import Image
from tqdm import tqdm

EXTENSIONES_VALIDAS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".gif",
    ".tiff", ".tif", ".webp", ".heic", ".heif",
}

# Score de opennsfw2: 0 = seguro, 1 = explicito.
UMBRAL_BAJO = 0.2   # por debajo -> no_explicito
UMBRAL_ALTO = 0.7   # por encima -> explicito
# entre medio -> revisar_manual

TAGS_FECHA_EXIF = (36867, 306)  # DateTimeOriginal, DateTime


def obtener_fecha_foto(ruta: Path) -> datetime:
    try:
        with Image.open(ruta) as img:
            exif = img.getexif()
            for tag in TAGS_FECHA_EXIF:
                valor = exif.get(tag)
                if valor:
                    return datetime.strptime(valor, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return datetime.fromtimestamp(ruta.stat().st_mtime)


def ruta_destino_sin_colision(destino: Path) -> Path:
    if not destino.exists():
        return destino
    base, ext = destino.stem, destino.suffix
    contador = 1
    while True:
        candidato = destino.with_name(f"{base}_{contador}{ext}")
        if not candidato.exists():
            return candidato
        contador += 1


def main():
    print("=== Clasificador de fotos (explicito / no explicito) ===\n")

    origen = input("Ruta de la carpeta con las fotos a clasificar: ").strip()
    origen_path = Path(origen).expanduser().resolve()
    if not origen_path.is_dir():
        print(f"La ruta '{origen_path}' no es una carpeta valida.")
        sys.exit(1)

    destino_default = origen_path.parent / f"{origen_path.name}_clasificado"
    destino = input(f"Carpeta destino [{destino_default}]: ").strip()
    destino_path = Path(destino).expanduser().resolve() if destino else destino_default

    if destino_path == origen_path or origen_path in destino_path.parents:
        print("La carpeta destino no puede ser la misma carpeta de origen ni estar dentro de ella.")
        sys.exit(1)

    print("\nBuscando imagenes...")
    imagenes = [
        p for p in origen_path.rglob("*")
        if p.is_file() and p.suffix.lower() in EXTENSIONES_VALIDAS
    ]
    print(f"Se encontraron {len(imagenes)} imagenes.\n")
    if not imagenes:
        print("No hay imagenes para procesar.")
        return

    confirmacion = input(f"Se van a MOVER a: {destino_path}\n¿Continuar? (s/n): ").strip().lower()
    if confirmacion != "s":
        print("Cancelado.")
        return

    print("\nCargando modelo de clasificacion (puede tardar la primera vez)...")
    import opennsfw2 as n2

    conteos = {"no_explicito": 0, "explicito": 0, "revisar_manual": 0, "error": 0}

    for ruta in tqdm(imagenes, desc="Clasificando", unit="foto"):
        try:
            score = n2.predict_image(str(ruta))
        except Exception as e:
            tqdm.write(f"  [ERROR] No se pudo analizar {ruta}: {e}")
            conteos["error"] += 1
            continue

        if score < UMBRAL_BAJO:
            categoria = "no_explicito"
        elif score > UMBRAL_ALTO:
            categoria = "explicito"
        else:
            categoria = "revisar_manual"

        fecha = obtener_fecha_foto(ruta)
        subcarpeta_fecha = f"{fecha.year:04d}/{fecha.year:04d}-{fecha.month:02d}"

        carpeta_destino_final = destino_path / categoria / subcarpeta_fecha
        carpeta_destino_final.mkdir(parents=True, exist_ok=True)

        destino_archivo = ruta_destino_sin_colision(carpeta_destino_final / ruta.name)
        shutil.move(str(ruta), str(destino_archivo))
        conteos[categoria] += 1

    print("\n=== Resumen ===")
    for categoria, cantidad in conteos.items():
        print(f"  {categoria}: {cantidad}")
    print(f"\nRevisa especialmente la carpeta 'revisar_manual' (score entre {UMBRAL_BAJO} y {UMBRAL_ALTO}), "
          "el modelo no es 100% preciso.")


if __name__ == "__main__":
    main()
