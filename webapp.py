#!/usr/bin/env python3
"""Frontend Tinder para el post-consola: revisa lo que queda del clasificado por IA."""

from __future__ import annotations

import itertools
import json
import os
import re
import shutil
import sys
import threading
import webbrowser
from dataclasses import dataclass, field
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

# Nombres aceptados para cada categoría (ya normalizados: minúsculas, "_" en vez de espacios/guiones).
ALIAS_CATEGORIAS = {
    "explicito": {"explicito", "explicitos", "explicitas", "explicit"},
    "no_explicito": {
        "no_explicito",
        "no_explicitos",
        "no_explicitas",
        "non_explicit",
        "nonexplicit",
        "not_explicit",
        "safe",
    },
    "revisar_manual": {
        "revisar_manual",
        "revisar",
        "force_revisit",
        "forced_revisit",
        "revisit",
        "review",
        "manual_review",
    },
}

CONFIG_PATH = Path.home() / ".clasificar_fotos" / "config.json"
DESTINO_POR_DEFECTO = Path.home() / "FotosClasificadas"
MAX_PREVIEWS_EXTRA = 2

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
    return sum(1 for p in carpeta.rglob("*") if es_imagen(p))


def normalizar_nombre(nombre: str) -> str:
    return re.sub(r"[\s\-]+", "_", nombre.strip().lower())


def categoria_de(nombre: str) -> str | None:
    clave = normalizar_nombre(nombre)
    for canonica, alias in ALIAS_CATEGORIAS.items():
        if clave in alias:
            return canonica
    return None


def categorias_en(carpeta: Path) -> dict[str, list[Path]]:
    """Subcarpetas directas de `carpeta` que son una categoría de la consola (con alias)."""
    encontradas: dict[str, list[Path]] = {}
    try:
        hijos = sorted(carpeta.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return encontradas
    for hijo in hijos:
        if not hijo.is_dir():
            continue
        categoria = categoria_de(hijo.name)
        if categoria:
            encontradas.setdefault(categoria, []).append(hijo)
    return encontradas


def es_resultado_consola(ruta: Path) -> bool:
    return bool(categorias_en(ruta))


def etiqueta_lote(lote: Path, raiz: Path) -> str:
    """Nombre del lote dentro del cúmulo: ruta relativa a la raíz elegida, sin el sufijo _clasificado."""
    try:
        partes = list(lote.relative_to(raiz).parts)
    except ValueError:
        partes = []
    if not partes:
        partes = [lote.name]
    ultimo = partes[-1]
    if ultimo.endswith("_clasificado") and len(ultimo) > len("_clasificado"):
        partes[-1] = ultimo[: -len("_clasificado")]
    return "/".join(partes)


@dataclass
class Lote:
    path: Path
    etiqueta: str
    categorias: dict[str, list[Path]] = field(default_factory=dict)

    @classmethod
    def desde(cls, path: Path, raiz: Path) -> "Lote":
        return cls(path=path, etiqueta=etiqueta_lote(path, raiz), categorias=categorias_en(path))


@dataclass
class Item:
    id: int
    foto: Path
    lote: Lote
    categoria: str
    relativo: Path


def descubrir_lotes(raiz: Path, destino: Path | None = None) -> list[Lote]:
    """Busca, a cualquier profundidad, carpetas que tengan subcarpetas explicito/no_explicito/revisar_manual."""
    destino_resuelto = destino.resolve() if destino else None
    lotes: list[Lote] = []
    for actual, dirnames, _ in os.walk(raiz):
        carpeta = Path(actual)
        if destino_resuelto and esta_dentro(carpeta, destino_resuelto):
            dirnames[:] = []
            continue
        dirnames[:] = sorted(
            (d for d in dirnames if not d.startswith(".")),
            key=str.lower,
        )
        if any(categoria_de(d) for d in dirnames):
            lotes.append(Lote.desde(carpeta, raiz))
            # No bajamos dentro de las categorías: ahí solo hay fotos (Camara/2024/2024-01...).
            dirnames[:] = [d for d in dirnames if not categoria_de(d)]
    return lotes


def resolver_resultado_consola(ruta: Path, destino: Path | None = None) -> tuple[Path, list[Lote], str | None]:
    """Devuelve (raíz, lotes encontrados, filtro opcional de categoría)."""
    categoria = categoria_de(ruta.name)
    if categoria and es_resultado_consola(ruta.parent):
        return ruta.parent, [Lote.desde(ruta.parent, ruta.parent)], categoria
    lotes = descubrir_lotes(ruta, destino)
    if lotes:
        return ruta, lotes, None
    vecino = ruta.parent / f"{ruta.name}_clasificado"
    if vecino.is_dir() and es_resultado_consola(vecino):
        return vecino, [Lote.desde(vecino, vecino)], None
    raise ValueError(
        "No encontré resultados de la consola acá adentro. "
        "Elegí una carpeta que tenga subcarpetas explicito / no_explicito / revisar_manual "
        "(o explicit / non-explicit / force-revisit), a cualquier profundidad, "
        "o la carpeta original: detecto la vecina _clasificado."
    )


def categoria_consola(foto: Path, raiz: Path) -> str | None:
    try:
        partes = foto.resolve().relative_to(raiz.resolve()).parts
    except ValueError:
        return None
    for parte in partes[:-1]:
        categoria = categoria_de(parte)
        if categoria:
            return categoria
    return None


def contar_lote(lote: Lote, destino: Path | None = None) -> dict[str, int]:
    return {
        nombre: sum(len(listar_imagenes(c, destino)) for c in lote.categorias.get(nombre, []))
        for nombre in CARPETAS_CONSOLA
    }


def resumen_consola(raiz: Path, lotes: list[Lote], destino: Path | None = None) -> dict:
    total = {nombre: 0 for nombre in CARPETAS_CONSOLA}
    detalle: list[dict] = []
    for lote in lotes:
        conteos = contar_lote(lote, destino)
        for nombre, cantidad in conteos.items():
            total[nombre] += cantidad
        detalle.append(
            {
                "etiqueta": lote.etiqueta,
                "path": str(lote.path),
                "conteos": conteos,
                "pendientes": conteos["explicito"] + conteos["revisar_manual"],
            }
        )
    return {
        "root": str(raiz),
        "es_resultado_consola": True,
        "conteos_consola": total,
        "pendientes": total["explicito"] + total["revisar_manual"],
        "lotes": detalle,
    }


def listar_pendientes(
    lotes: list[Lote],
    filtro: str | None,
    destino: Path | None,
    ids: itertools.count | None = None,
) -> list[Item]:
    if filtro in CARPETAS_CONSOLA:
        categorias = (filtro,)
    else:
        categorias = PENDIENTES_CONSOLA
    ids = ids or itertools.count(1)
    items: list[Item] = []
    for lote in lotes:
        for nombre in categorias:
            for carpeta in lote.categorias.get(nombre, []):
                for foto in listar_imagenes(carpeta, destino):
                    items.append(Item(next(ids), foto, lote, nombre, foto.relative_to(carpeta)))
    items.sort(key=lambda it: str(it.foto).lower())
    return items


def shortcuts_inicio() -> list[dict]:
    home = Path.home()
    candidatos = [
        ("Inicio", home),
        ("Escritorio", home / "Desktop"),
        ("Escritorio", home / "Escritorio"),
        ("Imágenes", home / "Pictures"),
        ("Documentos", home / "Documents"),
        ("Documentos", home / "Documentos"),
        ("Descargas", home / "Downloads"),
        ("Descargas", home / "Descargas"),
    ]
    if sys.platform == "darwin" and Path("/Volumes").is_dir():
        candidatos.append(("Discos", Path("/Volumes")))
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
        self.ids = itertools.count(1)
        self.origen: Path | None = None
        self.lotes: list[Lote] = []
        self.filtro: str | None = None
        self.resumen: dict | None = None
        self.cola: list[Item] = []
        self.total_origen = 0
        self.deshacer: list[dict] = []
        self._conteos: dict[str, int] | None = None

    def asegurar_destino(self) -> None:
        self.destino.mkdir(parents=True, exist_ok=True)
        for nombre in CARPETAS_RESULTADO:
            (self.destino / nombre).mkdir(parents=True, exist_ok=True)

    def set_destino(self, ruta: str) -> None:
        nuevo = Path(ruta).expanduser().resolve()
        if nuevo.exists() and not nuevo.is_dir():
            raise ValueError("El destino tiene que ser una carpeta.")
        if self.origen and esta_dentro(self.origen, nuevo):
            raise ValueError("El destino no puede contener la carpeta que estás revisando.")
        self.destino = nuevo
        self._conteos = None
        self.asegurar_destino()
        if self.persistir:
            cfg = cargar_config()
            cfg["destino"] = str(self.destino)
            guardar_config(cfg)

    def _resolver(self, ruta: str) -> tuple[Path, list[Lote], str | None]:
        origen = Path(ruta).expanduser().resolve()
        if not origen.is_dir():
            raise ValueError("Esa ruta no es una carpeta válida.")
        if self.destino.exists() and esta_dentro(origen, self.destino.resolve()):
            raise ValueError("No elijas una carpeta que esté dentro del destino final.")
        return resolver_resultado_consola(origen, self.destino)

    def inspeccionar(self, ruta: str) -> dict:
        raiz, lotes, filtro = self._resolver(ruta)
        info = resumen_consola(raiz, lotes, self.destino)
        info["filtro"] = filtro
        info["elegida"] = str(Path(ruta).expanduser().resolve())
        return info

    def set_origen(self, ruta: str, pasar_normales: bool = False) -> dict:
        raiz, lotes, filtro = self._resolver(ruta)
        self.asegurar_destino()
        movidas_normales = 0
        if pasar_normales and filtro is None:
            for lote in lotes:
                movidas_normales += self._mover_categoria(lote, "no_explicito", "normales")
        self.origen = raiz
        self.lotes = lotes
        self.filtro = filtro
        self.resumen = resumen_consola(raiz, lotes, self.destino)
        self.resumen["filtro"] = filtro
        self.cola = listar_pendientes(lotes, filtro, self.destino, self.ids)
        self.total_origen = len(self.cola)
        self.deshacer = []
        estado = self.estado()
        estado["movidas_normales"] = movidas_normales
        return estado

    def _destino_de(self, accion: str, lote: Lote, relativo: Path) -> Path:
        return self.destino / ACCIONES[accion] / Path(lote.etiqueta) / relativo

    def _mover(self, origen: Path, destino: Path) -> Path:
        destino.parent.mkdir(parents=True, exist_ok=True)
        final = ruta_destino_sin_colision(destino)
        shutil.move(str(origen), str(final))
        return final

    def _mover_categoria(self, lote: Lote, categoria: str, accion: str) -> int:
        movidas = 0
        for carpeta in lote.categorias.get(categoria, []):
            for foto in listar_imagenes(carpeta, self.destino):
                self._mover(foto, self._destino_de(accion, lote, foto.relative_to(carpeta)))
                movidas += 1
        if movidas and self._conteos is not None:
            self._conteos[accion] += movidas
        return movidas

    def actual(self) -> Path | None:
        return self.cola[0].foto if self.cola else None

    def item_por_id(self, item_id: int) -> Item | None:
        for item in self.cola[: MAX_PREVIEWS_EXTRA + 1]:
            if item.id == item_id:
                return item
        return None

    def conteos(self) -> dict[str, int]:
        if self._conteos is None:
            self.asegurar_destino()
            self._conteos = {nombre: contar_en_carpeta(self.destino / nombre) for nombre in CARPETAS_RESULTADO}
        return dict(self._conteos)

    def estado(self) -> dict:
        item = self.cola[0] if self.cola else None
        procesadas = self.total_origen - len(self.cola)
        return {
            "destino": str(self.destino),
            "origen": str(self.origen) if self.origen else None,
            "fase": "review" if item else ("done" if self.origen else "setup"),
            "foto": self._meta(item) if item else None,
            "siguientes": [self._meta(it) for it in self.cola[1 : MAX_PREVIEWS_EXTRA + 1]],
            "indice": procesadas + 1 if item else self.total_origen,
            "total": self.total_origen,
            "restantes": len(self.cola),
            "conteos": self.conteos(),
            "puede_deshacer": bool(self.deshacer),
            "ultima_accion": self.deshacer[-1]["accion"] if self.deshacer else None,
            "resumen_consola": self.resumen,
            "filtro": self.filtro,
        }

    def _meta(self, item: Item) -> dict:
        relativo = "/".join((item.lote.etiqueta, item.categoria, *item.relativo.parts))
        return {
            "id": item.id,
            "nombre": item.foto.name,
            "relativo": relativo.replace("\\", "/"),
            "lote": item.lote.etiqueta,
            "subcarpeta": "/".join(item.relativo.parts[:-1]),
            "preview": f"/api/preview/{item.id}",
            "categoria_consola": item.categoria,
        }

    def aplicar(self, accion: str) -> dict:
        if accion not in ACCIONES:
            raise ValueError("Acción desconocida.")
        item = None
        while self.cola:
            candidato = self.cola.pop(0)
            if candidato.foto.exists():
                item = candidato
                break
        if item is None:
            raise ValueError("No hay foto para clasificar.")
        destino_archivo = self._mover(item.foto, self._destino_de(accion, item.lote, item.relativo))
        self.deshacer.append(
            {
                "origen_original": str(item.foto),
                "destino": str(destino_archivo),
                "accion": accion,
                "item": item,
            }
        )
        if len(self.deshacer) > 30:
            self.deshacer.pop(0)
        if self._conteos is not None:
            self._conteos[accion] += 1
        return self.estado()

    def deshacer_ultima(self) -> dict:
        if not self.deshacer:
            raise ValueError("No hay nada para deshacer.")
        ultimo = self.deshacer.pop()
        movido = Path(ultimo["destino"])
        volver_a = Path(ultimo["origen_original"])
        if not movido.exists():
            raise ValueError("No encuentro el archivo para deshacer.")
        destino_vuelta = self._mover(movido, volver_a)
        item: Item = ultimo["item"]
        self.cola.insert(0, Item(next(self.ids), destino_vuelta, item.lote, item.categoria, item.relativo))
        if self._conteos is not None:
            self._conteos[ultimo["accion"]] = max(0, self._conteos[ultimo["accion"]] - 1)
        return self.estado()

    def cerrar_origen(self) -> dict:
        self.origen = None
        self.lotes = []
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
        try:
            if not hijo.is_dir() or hijo.name.startswith("."):
                continue
        except OSError:
            continue
        item = {"nombre": hijo.name, "path": str(hijo)}
        categoria = categoria_de(hijo.name)
        if categoria:
            item["categoria"] = categoria
        elif hijo.name.endswith("_clasificado") or es_resultado_consola(hijo):
            item["es_resultado_consola"] = True
        dirs.append(item)

    fotos = sum(1 for p in entradas if es_imagen(p))
    padre = None if ruta.parent == ruta else str(ruta.parent)
    # Solo miramos el nivel actual: explorar tiene que ser instantáneo aunque estés en tu home.
    consola = None
    if es_resultado_consola(ruta):
        consola = resumen_consola(ruta, [Lote.desde(ruta, ruta)])
        consola["filtro"] = None
    elif categoria_de(ruta.name) and es_resultado_consola(ruta.parent):
        consola = resumen_consola(ruta.parent, [Lote.desde(ruta.parent, ruta.parent)])
        consola["filtro"] = categoria_de(ruta.name)
    return jsonify(
        {
            "ok": True,
            "path": str(ruta),
            "parent": padre,
            "dirs": dirs,
            "fotos_aqui": fotos,
            "shortcuts": shortcuts_inicio(),
            "consola": consola,
            "lotes_hijos": sum(1 for d in dirs if d.get("es_resultado_consola")),
        }
    )


@app.get("/api/preview/<int:item_id>")
def api_preview(item_id: int):
    with sesion.lock:
        item = sesion.item_por_id(item_id)
        if item is None:
            abort(404)
        foto = item.foto
    if not foto.exists():
        abort(404)
    try:
        with Image.open(foto) as img:
            img = img.convert("RGB")
            img.thumbnail((1600, 1600))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85, optimize=True)
            buf.seek(0)
            resp = send_file(buf, mimetype="image/jpeg")
    except Exception:
        resp = send_file(foto)
    # El id es único por foto en la cola: el navegador puede reutilizar la precarga.
    resp.headers["Cache-Control"] = "private, max-age=600"
    return resp


def main() -> None:
    sesion.asegurar_destino()
    port = int(os.environ.get("CLASIFICAR_PORT", "5055"))
    url = f"http://127.0.0.1:{port}"
    print("=== Revisión Tinder (post-consola) ===")
    print("Esto NO clasifica con IA: actúa sobre lo que dejó ejecutar.bat / Clasificar Fotos.app.")
    print("Podés elegir un *_clasificado o una carpeta madre con varios adentro.")
    print(f"Abrí esta dirección en el navegador: {url}")
    print("Revisa lo que queda (explicito + revisar_manual) y se acumula en:")
    print(f"  {sesion.destino}")
    print("    normales/<lote>/<subcarpetas>/")
    print("    explicitas_guardar/<lote>/<subcarpetas>/")
    print("    explicitas_borrar/<lote>/<subcarpetas>/")
    print("Cerrá esta ventana para apagar el servidor.\n")
    if os.environ.get("CLASIFICAR_NO_BROWSER") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
