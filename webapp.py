#!/usr/bin/env python3
"""Frontend Tinder para el post-consola: revisa lo que queda del clasificado por IA."""

from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import webbrowser
from io import BytesIO
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, send_from_directory

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:
    pass

from PIL import Image

EXTENSIONES_VALIDAS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".gif",
    ".tiff",
    ".tif",
    ".webp",
    ".heic",
    ".heif",
}

ACCIONES = {
    "normales": "normales",
    "explicitas_guardar": "explicitas_guardar",
    "explicitas_borrar": "explicitas_borrar",
}

CARPETAS_RESULTADO = tuple(ACCIONES.values())
CARPETAS_CONSOLA = ("explicito", "no_explicito", "revisar_manual")
PENDIENTES_CONSOLA = ("explicito", "revisar_manual")
CONFIG_PATH = Path.home() / ".clasificar_fotos" / "config.json"
DESTINO_POR_DEFECTO = Path.home() / "FotosClasificadas"

ROOT = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="/static")


def esta_dentro(ruta: Path, raiz: Path) -> bool:
    try:
        ruta.resolve().relative_to(raiz.resolve())
        return True
    except ValueError:
        return False


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


def es_imagen(ruta: Path) -> bool:
    return ruta.is_file() and ruta.suffix.lower() in EXTENSIONES_VALIDAS


def listar_imagenes(origen: Path, destino: Path | None = None) -> list[Path]:
    imagenes: list[Path] = []
    destino_resuelto = destino.resolve() if destino else None
    for ruta in origen.rglob("*"):
        if not es_imagen(ruta):
            continue
        if destino_resuelto and esta_dentro(ruta, destino_resuelto):
            continue
        imagenes.append(ruta)
    imagenes.sort(key=lambda p: str(p).lower())
    return imagenes


def contar_en_carpeta(carpeta: Path) -> int:
    if not carpeta.is_dir():
        return 0
    return sum(1 for p in carpeta.iterdir() if es_imagen(p))


def es_resultado_consola(ruta: Path) -> bool:
    return any((ruta / nombre).is_dir() for nombre in CARPETAS_CONSOLA)


def resolver_resultado_consola(ruta: Path) -> tuple[Path, str | None]:
    """Devuelve (carpeta _clasificado, filtro opcional de categoría)."""
    if ruta.name in CARPETAS_CONSOLA and es_resultado_consola(ruta.parent):
        return ruta.parent, ruta.name
    if es_resultado_consola(ruta):
        return ruta, None
    vecino = ruta.parent / f"{ruta.name}_clasificado"
    if vecino.is_dir() and es_resultado_consola(vecino):
        return vecino, None
    raise ValueError(
        "Esta carpeta no parece el resultado de la consola. "
        "Primero corré el clasificador (ejecutar.bat / Clasificar Fotos.app) "
        "y después elegí la carpeta que termina en _clasificado "
        "(o la original: detecto la vecina _clasificado)."
    )


def categoria_consola(foto: Path, raiz: Path) -> str | None:
    try:
        primero = foto.resolve().relative_to(raiz.resolve()).parts[0]
    except (ValueError, IndexError):
        return None
    if primero in CARPETAS_CONSOLA:
        return primero
    return None


def resumen_consola(raiz: Path, destino: Path | None = None) -> dict:
    conteos = {
        nombre: len(listar_imagenes(raiz / nombre, destino)) if (raiz / nombre).is_dir() else 0
        for nombre in CARPETAS_CONSOLA
    }
    return {
        "root": str(raiz),
        "es_resultado_consola": True,
        "conteos_consola": conteos,
        "pendientes": conteos["explicito"] + conteos["revisar_manual"],
    }


def listar_pendientes(raiz: Path, filtro: str | None, destino: Path | None) -> list[Path]:
    if filtro == "no_explicito":
        categorias = ("no_explicito",)
    elif filtro in PENDIENTES_CONSOLA:
        categorias = (filtro,)
    else:
        categorias = PENDIENTES_CONSOLA
    fotos: list[Path] = []
    for nombre in categorias:
        carpeta = raiz / nombre
        if carpeta.is_dir():
            fotos.extend(listar_imagenes(carpeta, destino))
    fotos.sort(key=lambda p: str(p).lower())
    return fotos


def shortcuts_inicio() -> list[dict]:
    home = Path.home()
    candidatos = [
        ("Inicio", home),
        ("Escritorio", home / "Desktop"),
        ("Escritorio", home / "Escritorio"),
        ("Imágenes", home / "Pictures"),
        ("Imágenes", home / "Pictures"),
        ("Fotos", home / "Pictures"),
        ("Documentos", home / "Documents"),
        ("Documentos", home / "Documentos"),
        ("Descargas", home / "Downloads"),
        ("Descargas", home / "Descargas"),
    ]
    vistos: set[str] = set()
    out: list[dict] = []
    for nombre, ruta in candidatos:
        if not ruta.is_dir():
            continue
        clave = str(ruta.resolve())
        if clave in vistos:
            continue
        vistos.add(clave)
        out.append({"nombre": nombre, "path": clave})
    if sys.platform == "win32":
        for letra in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            unidad = Path(f"{letra}:/")
            if unidad.exists():
                clave = str(unidad.resolve())
                if clave not in vistos:
                    vistos.add(clave)
                    out.append({"nombre": f"Disco {letra}:", "path": clave})
    return out


def cargar_config() -> dict:
    if not CONFIG_PATH.exists():
        return {"destino": str(DESTINO_POR_DEFECTO)}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not data.get("destino"):
        data["destino"] = str(DESTINO_POR_DEFECTO)
    return data


def guardar_config(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class Sesion:
    def __init__(self, destino: str | Path | None = None, persistir: bool = True) -> None:
        self.lock = threading.Lock()
        self.persistir = persistir
        if destino:
            self.destino = Path(destino).expanduser()
        else:
            self.destino = Path(cargar_config()["destino"]).expanduser()
        self.origen: Path | None = None
        self.filtro: str | None = None
        self.resumen: dict | None = None
        self.cola: list[Path] = []
        self.total_origen = 0
        self.deshacer: list[dict] = []

    def asegurar_destino(self) -> None:
        self.destino.mkdir(parents=True, exist_ok=True)
        for nombre in CARPETAS_RESULTADO:
            (self.destino / nombre).mkdir(parents=True, exist_ok=True)

    def set_destino(self, ruta: str) -> None:
        nuevo = Path(ruta).expanduser().resolve()
        if nuevo.exists() and not nuevo.is_dir():
            raise ValueError("El destino tiene que ser una carpeta.")
        if self.origen and esta_dentro(self.origen, nuevo):
            raise ValueError("El destino no puede estar dentro de la carpeta que estás revisando.")
        self.destino = nuevo
        self.asegurar_destino()
        if self.persistir:
            cfg = cargar_config()
            cfg["destino"] = str(self.destino)
            guardar_config(cfg)

    def inspeccionar(self, ruta: str) -> dict:
        origen = Path(ruta).expanduser().resolve()
        if not origen.is_dir():
            raise ValueError("Esa ruta no es una carpeta válida.")
        raiz, filtro = resolver_resultado_consola(origen)
        info = resumen_consola(raiz, self.destino)
        info["filtro"] = filtro
        info["elegida"] = str(origen)
        return info

    def set_origen(self, ruta: str, pasar_normales: bool = False) -> dict:
        origen = Path(ruta).expanduser().resolve()
        if not origen.is_dir():
            raise ValueError("Esa ruta no es una carpeta válida.")
        raiz, filtro = resolver_resultado_consola(origen)
        if self.destino.exists() and esta_dentro(raiz, self.destino.resolve()):
            raise ValueError("No elijas una carpeta que esté dentro del destino final.")
        if raiz.resolve() == self.destino.resolve():
            raise ValueError("El origen y el destino no pueden ser la misma carpeta.")
        self.asegurar_destino()
        movidas_normales = 0
        if pasar_normales and filtro is None:
            movidas_normales = self._mover_categoria(raiz, "no_explicito", "normales")
        self.origen = raiz
        self.filtro = filtro
        self.resumen = resumen_consola(raiz, self.destino)
        self.resumen["filtro"] = filtro
        self.cola = listar_pendientes(raiz, filtro, self.destino)
        self.total_origen = len(self.cola)
        self.deshacer = []
        estado = self.estado()
        estado["movidas_normales"] = movidas_normales
        return estado

    def _mover_categoria(self, raiz: Path, categoria: str, accion: str) -> int:
        carpeta = raiz / categoria
        if not carpeta.is_dir():
            return 0
        movidas = 0
        for foto in listar_imagenes(carpeta, self.destino):
            destino_archivo = ruta_destino_sin_colision(self.destino / ACCIONES[accion] / foto.name)
            destino_archivo.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(foto), str(destino_archivo))
            movidas += 1
        return movidas

    def actual(self) -> Path | None:
        return self.cola[0] if self.cola else None

    def conteos(self) -> dict[str, int]:
        self.asegurar_destino()
        return {nombre: contar_en_carpeta(self.destino / nombre) for nombre in CARPETAS_RESULTADO}

    def estado(self) -> dict:
        foto = self.actual()
        procesadas = self.total_origen - len(self.cola)
        return {
            "destino": str(self.destino),
            "origen": str(self.origen) if self.origen else None,
            "fase": "review" if foto else ("done" if self.origen else "setup"),
            "foto": self._meta(foto) if foto else None,
            "indice": procesadas + 1 if foto else self.total_origen,
            "total": self.total_origen,
            "restantes": len(self.cola),
            "conteos": self.conteos(),
            "puede_deshacer": bool(self.deshacer),
            "resumen_consola": self.resumen,
            "filtro": self.filtro,
        }

    def _meta(self, foto: Path) -> dict:
        relativo = foto.name
        if self.origen:
            try:
                relativo = str(foto.relative_to(self.origen))
            except ValueError:
                relativo = foto.name
        return {
            "nombre": foto.name,
            "relativo": relativo.replace("\\", "/"),
            "preview": "/api/preview",
            "categoria_consola": categoria_consola(foto, self.origen) if self.origen else None,
        }

    def aplicar(self, accion: str) -> dict:
        if accion not in ACCIONES:
            raise ValueError("Acción desconocida.")
        foto = None
        while self.cola:
            candidato = self.cola.pop(0)
            if candidato.exists():
                foto = candidato
                break
        if foto is None:
            raise ValueError("No hay foto para clasificar.")
        carpeta = self.destino / ACCIONES[accion]
        carpeta.mkdir(parents=True, exist_ok=True)
        destino_archivo = ruta_destino_sin_colision(carpeta / foto.name)
        original = foto
        shutil.move(str(foto), str(destino_archivo))
        self.deshacer.append(
            {
                "origen_original": str(original),
                "destino": str(destino_archivo),
                "accion": accion,
            }
        )
        if len(self.deshacer) > 30:
            self.deshacer.pop(0)
        return self.estado()

    def deshacer_ultima(self) -> dict:
        if not self.deshacer:
            raise ValueError("No hay nada para deshacer.")
        ultimo = self.deshacer.pop()
        movido = Path(ultimo["destino"])
        volver_a = Path(ultimo["origen_original"])
        if not movido.exists():
            raise ValueError("No encuentro el archivo para deshacer.")
        volver_a.parent.mkdir(parents=True, exist_ok=True)
        destino_vuelta = ruta_destino_sin_colision(volver_a)
        shutil.move(str(movido), str(destino_vuelta))
        self.cola.insert(0, destino_vuelta)
        return self.estado()

    def cerrar_origen(self) -> dict:
        self.origen = None
        self.filtro = None
        self.resumen = None
        self.cola = []
        self.total_origen = 0
        self.deshacer = []
        return self.estado()


sesion = Sesion()


def _json_error(mensaje: str, codigo: int = 400):
    return jsonify({"ok": False, "error": mensaje}), codigo


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/estado")
def api_estado():
    with sesion.lock:
        return jsonify({"ok": True, **sesion.estado()})


@app.post("/api/destino")
def api_destino():
    data = request.get_json(silent=True) or {}
    ruta = (data.get("path") or "").strip()
    if not ruta:
        return _json_error("Falta la carpeta destino.")
    try:
        with sesion.lock:
            sesion.set_destino(ruta)
            return jsonify({"ok": True, **sesion.estado()})
    except ValueError as exc:
        return _json_error(str(exc))


@app.get("/api/inspeccionar")
def api_inspeccionar():
    ruta = (request.args.get("path") or "").strip()
    if not ruta:
        return _json_error("Falta la carpeta a inspeccionar.")
    try:
        with sesion.lock:
            return jsonify({"ok": True, **sesion.inspeccionar(ruta)})
    except ValueError as exc:
        return _json_error(str(exc))


@app.post("/api/origen")
def api_origen():
    data = request.get_json(silent=True) or {}
    ruta = (data.get("path") or "").strip()
    if not ruta:
        return _json_error("Falta la carpeta a revisar.")
    pasar = bool(data.get("pasar_normales"))
    try:
        with sesion.lock:
            return jsonify({"ok": True, **sesion.set_origen(ruta, pasar_normales=pasar)})
    except ValueError as exc:
        return _json_error(str(exc))


@app.post("/api/accion")
def api_accion():
    data = request.get_json(silent=True) or {}
    accion = (data.get("accion") or "").strip()
    try:
        with sesion.lock:
            return jsonify({"ok": True, **sesion.aplicar(accion)})
    except ValueError as exc:
        return _json_error(str(exc))


@app.post("/api/deshacer")
def api_deshacer():
    try:
        with sesion.lock:
            return jsonify({"ok": True, **sesion.deshacer_ultima()})
    except ValueError as exc:
        return _json_error(str(exc))


@app.post("/api/cerrar")
def api_cerrar():
    with sesion.lock:
        return jsonify({"ok": True, **sesion.cerrar_origen()})


@app.get("/api/explorar")
def api_explorar():
    crudo = request.args.get("path") or str(Path.home())
    ruta = Path(crudo).expanduser()
    try:
        ruta = ruta.resolve()
    except OSError:
        return _json_error("No pude abrir esa ruta.")
    if not ruta.exists():
        return _json_error("Esa carpeta no existe.")
    if not ruta.is_dir():
        return _json_error("Esa ruta no es una carpeta.")

    dirs: list[dict] = []
    try:
        entradas = list(ruta.iterdir())
    except PermissionError:
        return _json_error("No tengo permiso para entrar a esa carpeta.")

    for hijo in sorted(entradas, key=lambda p: p.name.lower()):
        if not hijo.is_dir():
            continue
        if hijo.name.startswith(".") and hijo.name not in {".", ".."}:
            continue
        dirs.append({"nombre": hijo.name, "path": str(hijo)})

    fotos = sum(1 for p in entradas if es_imagen(p))
    padre = None if ruta.parent == ruta else str(ruta.parent)
    consola = None
    try:
        raiz, filtro = resolver_resultado_consola(ruta)
        consola = resumen_consola(raiz)
        consola["filtro"] = filtro
    except ValueError:
        pass
    for item in dirs:
        hijo = Path(item["path"])
        if hijo.name.endswith("_clasificado") or es_resultado_consola(hijo):
            item["es_resultado_consola"] = True
    return jsonify(
        {
            "ok": True,
            "path": str(ruta),
            "parent": padre,
            "dirs": dirs,
            "fotos_aqui": fotos,
            "shortcuts": shortcuts_inicio(),
            "consola": consola,
        }
    )


@app.get("/api/preview")
def api_preview():
    with sesion.lock:
        foto = sesion.actual()
        if foto is None:
            abort(404)
        foto = Path(foto)
    if not foto.exists():
        abort(404)
    try:
        with Image.open(foto) as img:
            img = img.convert("RGB")
            img.thumbnail((1600, 1600))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85, optimize=True)
            buf.seek(0)
            return send_file(buf, mimetype="image/jpeg")
    except Exception:
        return send_file(foto)


def main() -> None:
    sesion.asegurar_destino()
    port = int(os.environ.get("CLASIFICAR_PORT", "5055"))
    url = f"http://127.0.0.1:{port}"
    print("=== Revisión Tinder (post-consola) ===")
    print("Esto NO clasifica con IA: actúa sobre la carpeta *_clasificado")
    print("que ya salió de ejecutar.bat / Clasificar Fotos.app.")
    print(f"Abrí esta dirección en el navegador: {url}")
    print("Revisa lo que queda (explicito + revisar_manual) y se acumula en:")
    print(f"  {sesion.destino}")
    print("    normales/")
    print("    explicitas_guardar/")
    print("    explicitas_borrar/")
    print("Cerrá esta ventana para apagar el servidor.\n")
    if os.environ.get("CLASIFICAR_NO_BROWSER") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
