#!/usr/bin/env python3
"""Tercera pasada: busca lo que se escapó (explícitas, zoofilia, documentos, capturas, tapas de disco, memes).

Usa dos modelos que corren en tu PC (no sube nada a internet):
  - NudeNet: detecta partes del cuerpo expuestas.
  - OpenCLIP: compara cada imagen con descripciones en texto ("una tapa de CD", "un documento", ...).

Deja una carpeta al lado de la elegida, con el sufijo "_pulido", que el front Tinder ya sabe leer:
  explicito/        -> casi seguro explícita (NudeNet, o NudeNet + CLIP de acuerdo)
  revisar_manual/   -> no parece una foto para guardar (documento, captura, tapa...) o explícita dudosa
  no_explicito/     -> foto normal
y un "motivos_pulido.json" con el porqué de cada una, que el Tinder muestra en la tarjeta.
"""

import json
import logging
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps
from tqdm import tqdm

# Reutiliza los formatos aceptados (y el soporte HEIC) y los helpers del paso 1.
from clasificar_fotos import EXTENSIONES_VALIDAS, limpiar_ruta_ingresada, ruta_destino_sin_colision

SUFIJO_SALIDA = "_pulido"
ARCHIVO_MOTIVOS = "motivos_pulido.json"

# --- NudeNet --------------------------------------------------------------
# Score minimo por clase para mandar la foto directo a explicito/.
UMBRALES_NUDENET = {
    "FEMALE_GENITALIA_EXPOSED": 0.45,
    "MALE_GENITALIA_EXPOSED": 0.45,
    "ANUS_EXPOSED": 0.45,
    "FEMALE_BREAST_EXPOSED": 0.55,
    "BUTTOCKS_EXPOSED": 0.60,
}
# Una deteccion de esas clases con score entre este valor y su umbral -> revisar_manual.
UMBRAL_NUDENET_DUDA = 0.30

NOMBRES_NUDENET = {
    "FEMALE_GENITALIA_EXPOSED": "genitales expuestos",
    "MALE_GENITALIA_EXPOSED": "genitales expuestos",
    "ANUS_EXPOSED": "ano expuesto",
    "FEMALE_BREAST_EXPOSED": "pechos expuestos",
    "BUTTOCKS_EXPOSED": "nalgas expuestas",
}

# --- OpenCLIP -------------------------------------------------------------
MODELO_CLIP = "ViT-B-32"
PESOS_CLIP = "laion2b_s34b_b79k"  # ~600 MB, se descarga solo la primera vez

# Cada categoria se describe con varias frases (en ingles, que es como entiende CLIP);
# se promedian y la imagen se reparte entre las categorias (suman 1).
CATEGORIAS_CLIP = {
    "foto": [
        "a personal photo", "a photo of people", "a portrait photo of a person", "a selfie",
        "a family photo", "a group photo of friends", "a photo of a landscape", "a photo of a cat",
        "a photo of a dog", "a photo of an animal", "a photo of food", "a photo of a drink",
        "a vacation photo", "a photo of a city street", "a photo of an object", "a photo of a vehicle",
        "a black and white photo", "a photo of the night sky", "a photo taken with a phone camera",
        "a photo of a party", "a photo of a baby",
    ],
    "explicito": [
        "a pornographic photo", "explicit sexual content", "a photo of a naked person showing genitals",
        "a photo of people having sex", "amateur porn",
    ],
    "zoofilia": [
        "a person having sex with an animal", "bestiality porn",
        "a sexual act between a naked human and an animal",
    ],
    "documento": [
        "a scanned document", "a photo of a paper document with text", "a receipt", "an invoice",
        "an ID card", "a page of a book", "a page of text", "handwritten notes", "a form", "a printed page",
    ],
    "captura": [
        "a screenshot", "a screenshot of a phone", "a screenshot of a chat conversation",
        "a screenshot of a website", "a screenshot of a computer screen",
    ],
    "tapa_disco": [
        "an album cover", "a CD cover", "a music album artwork", "a DVD cover", "a movie poster", "a book cover",
    ],
    "meme_dibujo": [
        "a meme", "an internet meme with text", "a cartoon", "a drawing", "a logo", "clip art",
        "a digital illustration",
    ],
}

CATEGORIAS_SEXUALES = ("explicito", "zoofilia")
# Probabilidad minima para marcar algo que no es una foto. meme_dibujo es la mas ruidosa
# (retratos de estudio o fotos muy editadas a veces caen ahi), por eso pide mas.
UMBRALES_NO_FOTO = {
    "documento": 0.50,
    "captura": 0.50,
    "tapa_disco": 0.50,
    "meme_dibujo": 0.75,
}
# CLIP solo, sin que NudeNet vea nada, a veces confunde paginas escaneadas o memes de animales
# con contenido sexual: por eso solo manda a explicito/ si esta muy seguro.
# Si ninguna categoria de "no foto" llega a su umbral pero entre todas se llevan casi todo
# y "foto" queda por debajo de esto, igual se marca (texto suelto, graficos raros).
UMBRAL_FOTO_MINIMO = 0.10
UMBRAL_CLIP_SEXUAL = 0.50        # desde aca -> revisar_manual (o explicito si NudeNet ve algo)
UMBRAL_CLIP_SEXUAL_SEGURO = 0.85  # desde aca -> explicito aunque NudeNet no vea nada
UMBRAL_NUDENET_APOYO = 0.25       # cualquier parte expuesta con este score confirma a CLIP

NOMBRES_CLIP = {
    "explicito": "contenido sexual",
    "zoofilia": "posible zoofilia",
    "documento": "documento",
    "captura": "captura de pantalla",
    "tapa_disco": "tapa de disco / película",
    "meme_dibujo": "meme / dibujo",
}

# Nombres de archivo tipicos de capturas (Android, iPhone, Windows, Mac en español e ingles).
PATRON_CAPTURA = re.compile(r"screenshot|screen[\s_-]?shot|captura|recorte|snip", re.IGNORECASE)

LADO_MAX = 640       # alcanza para ambos modelos y acelera mucho la lectura
TAMANO_LOTE = 16     # imagenes por pasada de CLIP
GUARDAR_CADA = 25    # cada cuantas fotos se escribe motivos_pulido.json


def decidir(detecciones: list[dict], probs: dict[str, float], nombre: str) -> tuple[str, str]:
    """Devuelve (categoria, motivo legible) a partir de lo que vieron NudeNet y CLIP."""
    expuestas = [d for d in detecciones if d["class"] in UMBRALES_NUDENET]
    mejor = max(expuestas, key=lambda d: d["score"], default=None)

    # 1) NudeNet seguro.
    for d in sorted(expuestas, key=lambda d: d["score"], reverse=True):
        if d["score"] >= UMBRALES_NUDENET[d["class"]]:
            return "explicito", f"NudeNet: {NOMBRES_NUDENET[d['class']]} ({d['score']:.0%})"

    # 2) CLIP ve algo sexual: lo confirma NudeNet o esta muy seguro.
    sexual = sum(probs.get(c, 0.0) for c in CATEGORIAS_SEXUALES)
    clase_sexual = max(CATEGORIAS_SEXUALES, key=lambda c: probs.get(c, 0.0))
    if sexual >= UMBRAL_CLIP_SEXUAL:
        texto = f"CLIP: {NOMBRES_CLIP[clase_sexual]} ({sexual:.0%})"
        apoyo = mejor is not None and mejor["score"] >= UMBRAL_NUDENET_APOYO
        if apoyo:
            return "explicito", f"{texto} + NudeNet: {NOMBRES_NUDENET[mejor['class']]} ({mejor['score']:.0%})"
        if sexual >= UMBRAL_CLIP_SEXUAL_SEGURO:
            return "explicito", texto
        # Sin NudeNet, una pagina escaneada o un meme de animales tambien pueden caer aca: se nombran ambas.
        no_foto = max(UMBRALES_NO_FOTO, key=lambda c: probs.get(c, 0.0))
        if probs.get(no_foto, 0.0) >= 0.20:
            texto = f"CLIP dudoso: {NOMBRES_CLIP[no_foto]} ({probs[no_foto]:.0%}) o {NOMBRES_CLIP[clase_sexual]} ({sexual:.0%})"
        return "revisar_manual", texto

    # 3) NudeNet dudoso.
    if mejor is not None and mejor["score"] >= UMBRAL_NUDENET_DUDA:
        return "revisar_manual", f"NudeNet dudoso: {NOMBRES_NUDENET[mejor['class']]} ({mejor['score']:.0%})"

    # 4) No parece una foto para guardar.
    no_foto = max(UMBRALES_NO_FOTO, key=lambda c: probs.get(c, 0.0))
    if probs.get(no_foto, 0.0) >= UMBRALES_NO_FOTO[no_foto] or probs.get("foto", 1.0) < UMBRAL_FOTO_MINIMO:
        return "revisar_manual", f"CLIP: {NOMBRES_CLIP[no_foto]} ({probs.get(no_foto, 0.0):.0%})"
    if PATRON_CAPTURA.search(nombre):
        return "revisar_manual", "captura de pantalla (por el nombre del archivo)"

    return "no_explicito", ""


class Analizador:
    """Carga NudeNet y OpenCLIP una sola vez y analiza imagenes de a lotes."""

    def __init__(self) -> None:
        logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
        import numpy as np
        import open_clip
        import torch
        from nudenet import NudeDetector

        self.np = np
        self.torch = torch
        self.nudenet = NudeDetector()
        self.modelo, _, self.preproceso = open_clip.create_model_and_transforms(MODELO_CLIP, pretrained=PESOS_CLIP)
        self.modelo.eval()
        tokenizer = open_clip.get_tokenizer(MODELO_CLIP)
        self.categorias = list(CATEGORIAS_CLIP)
        with torch.no_grad():
            textos = []
            for frases in CATEGORIAS_CLIP.values():
                emb = self.modelo.encode_text(tokenizer(frases))
                emb = emb / emb.norm(dim=-1, keepdim=True)
                emb = emb.mean(dim=0)
                textos.append(emb / emb.norm())
            self.textos = torch.stack(textos)

    def analizar(self, imagenes: list[Image.Image]) -> list[tuple[list[dict], dict[str, float]]]:
        torch, np = self.torch, self.np
        with torch.no_grad():
            lote = torch.stack([self.preproceso(img) for img in imagenes])
            emb = self.modelo.encode_image(lote)
            emb = emb / emb.norm(dim=-1, keepdim=True)
            probs = (100.0 * emb @ self.textos.T).softmax(dim=-1).tolist()
        resultados = []
        for img, fila in zip(imagenes, probs):
            # NudeNet espera BGR como cv2.imread; se lo pasamos ya leido para soportar HEIC y rutas con tildes.
            bgr = np.ascontiguousarray(np.asarray(img)[:, :, ::-1])
            resultados.append((self.nudenet.detect(bgr), dict(zip(self.categorias, fila))))
        return resultados


def cargar_imagen(ruta: Path) -> Image.Image | None:
    try:
        with Image.open(ruta) as img:
            img.draft("RGB", (LADO_MAX, LADO_MAX))  # JPEG: decodifica ya reducida
            img = ImageOps.exif_transpose(img)  # fotos de celular giradas
            img = img.convert("RGB")
            img.thumbnail((LADO_MAX, LADO_MAX))
            return img
    except Exception:
        return None


def cargar_motivos(destino: Path) -> dict:
    try:
        return json.loads((destino / ARCHIVO_MOTIVOS).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def guardar_motivos(destino: Path, motivos: dict) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    tmp = destino / f"{ARCHIVO_MOTIVOS}.tmp"
    tmp.write_text(json.dumps(motivos, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp, destino / ARCHIVO_MOTIVOS)


def aviso_destino_tinder(destino_path: Path) -> None:
    """Si la salida queda dentro del destino del Tinder, avisa: el Tinder no revisa carpetas de su propio destino."""
    try:
        cfg = json.loads((Path.home() / ".clasificar_fotos" / "config.json").read_text(encoding="utf-8"))
        tinder = Path(cfg.get("destino") or "").expanduser().resolve()
        destino_path.resolve().relative_to(tinder)
    except (OSError, ValueError, json.JSONDecodeError):
        return
    print(f"\nOjo: {destino_path.name} queda dentro del destino del Tinder ({tinder}).")
    print("Cuando abras el Tinder, elegí un destino NUEVO para esta pasada (por ejemplo FotosFinales).")


def main():
    print("=== Pulido final (NudeNet + OpenCLIP) ===\n")

    if len(sys.argv) > 1:
        origen = sys.argv[1]
    else:
        origen = limpiar_ruta_ingresada(input("Arrastra aca la carpeta con las fotos que ya ordenaste y presiona Enter: "))
    origen_path = Path(origen).expanduser().resolve()
    if not origen_path.is_dir():
        print(f"La ruta '{origen_path}' no es una carpeta valida.")
        sys.exit(1)

    destino_path = origen_path.parent / f"{origen_path.name}{SUFIJO_SALIDA}"
    print(f"Carpeta de origen:  {origen_path}")
    print(f"Carpeta de destino: {destino_path}")

    print("\nBuscando imagenes...")
    imagenes = sorted(
        (p for p in origen_path.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONES_VALIDAS),
        key=lambda p: str(p).lower(),
    )
    print(f"Se encontraron {len(imagenes)} imagenes.\n")
    if not imagenes:
        print("No hay imagenes para procesar.")
        return

    confirmacion = input(f"Se van a MOVER a: {destino_path}\n¿Continuar? (s/n): ").strip().lower()
    if confirmacion != "s":
        print("Cancelado.")
        return

    print("\nCargando NudeNet y OpenCLIP (la primera vez descarga unos 600 MB, despues queda guardado)...")
    try:
        analizador = Analizador()
    except ImportError as e:
        print(f"\nFalta instalar algo para el pulido ({e.name}).")
        print("Windows: volve a correr 'instalar.bat'.")
        print("Mac: uv pip install --python .venv/bin/python -r requirements.txt")
        sys.exit(1)

    conteos = {"no_explicito": 0, "explicito": 0, "revisar_manual": 0, "error": 0}
    motivos = cargar_motivos(destino_path)
    pendientes_guardar = 0

    def mover(ruta: Path, categoria: str, motivo: str) -> None:
        nonlocal pendientes_guardar
        # Se conserva la estructura que ya tenias (ej. normales/pendrive/Camara/2024/2024-07/).
        carpeta_final = destino_path / categoria / ruta.parent.relative_to(origen_path)
        carpeta_final.mkdir(parents=True, exist_ok=True)
        final = ruta_destino_sin_colision(carpeta_final / ruta.name)
        shutil.move(str(ruta), str(final))
        conteos[categoria] += 1
        if motivo:
            motivos[final.relative_to(destino_path).as_posix()] = motivo
            pendientes_guardar += 1
            if pendientes_guardar >= GUARDAR_CADA:
                guardar_motivos(destino_path, motivos)
                pendientes_guardar = 0

    try:
        with ThreadPoolExecutor(max_workers=4) as lector, tqdm(total=len(imagenes), desc="Puliendo", unit="foto") as barra:
            for inicio in range(0, len(imagenes), TAMANO_LOTE):
                rutas = imagenes[inicio : inicio + TAMANO_LOTE]
                cargadas = list(lector.map(cargar_imagen, rutas))
                validas = [(r, img) for r, img in zip(rutas, cargadas) if img is not None]
                for r, img in zip(rutas, cargadas):
                    if img is None:
                        tqdm.write(f"  [ERROR] No se pudo abrir {r}")
                        conteos["error"] += 1
                try:
                    resultados = analizador.analizar([img for _, img in validas]) if validas else []
                except Exception as e:
                    tqdm.write(f"  [ERROR] Fallo el analisis de un lote ({e}); se dejan en el origen.")
                    conteos["error"] += len(validas)
                    resultados, validas = [], []
                for (ruta, _), (detecciones, probs) in zip(validas, resultados):
                    categoria, motivo = decidir(detecciones, probs, ruta.name)
                    mover(ruta, categoria, motivo)
                barra.update(len(rutas))
    finally:
        if motivos:
            guardar_motivos(destino_path, motivos)

    print("\n=== Resumen ===")
    for categoria, cantidad in conteos.items():
        print(f"  {categoria}: {cantidad}")
    print(f"\nEl porque de cada una quedo en {destino_path / ARCHIVO_MOTIVOS}")
    print("Ahora abri el Tinder (ejecutar_web) y elegi la carpeta "
          f"'{destino_path.name}' para decidir explicito y revisar_manual.")
    if conteos["error"]:
        print("Las que dieron error quedaron en la carpeta de origen, sin tocar.")
    aviso_destino_tinder(destino_path)


if __name__ == "__main__":
    main()
