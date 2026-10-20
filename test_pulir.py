#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

import pulir_fotos
import webapp


def probs(**valores: float) -> dict[str, float]:
    base = {c: 0.0 for c in pulir_fotos.CATEGORIAS_CLIP}
    base.update(valores)
    base["foto"] = valores.get("foto", max(0.0, 1.0 - sum(valores.values())))
    return base


def nn(clase: str, score: float) -> dict:
    return {"class": clase, "score": score, "box": [0, 0, 1, 1]}


class DecidirTests(unittest.TestCase):
    def test_foto_normal_queda(self) -> None:
        self.assertEqual(pulir_fotos.decidir([nn("FACE_FEMALE", 0.9)], probs(foto=0.8, meme_dibujo=0.2), "IMG_1.jpg"),
                         ("no_explicito", ""))

    def test_nudenet_seguro_es_explicito(self) -> None:
        cat, motivo = pulir_fotos.decidir([nn("MALE_GENITALIA_EXPOSED", 0.7)], probs(foto=0.9), "a.jpg")
        self.assertEqual(cat, "explicito")
        self.assertIn("NudeNet", motivo)

    def test_nudenet_dudoso_va_a_revisar(self) -> None:
        cat, motivo = pulir_fotos.decidir([nn("FEMALE_BREAST_EXPOSED", 0.4)], probs(foto=0.9), "a.jpg")
        self.assertEqual(cat, "revisar_manual")
        self.assertIn("dudoso", motivo)

    def test_clip_sexual_con_apoyo_de_nudenet_es_explicito(self) -> None:
        cat, motivo = pulir_fotos.decidir([nn("BUTTOCKS_EXPOSED", 0.3)], probs(zoofilia=0.6), "a.jpg")
        self.assertEqual(cat, "explicito")
        self.assertIn("zoofilia", motivo)

    def test_clip_sexual_solo_va_a_revisar_y_nombra_la_alternativa(self) -> None:
        cat, motivo = pulir_fotos.decidir([], probs(explicito=0.6, documento=0.3), "pagina.png")
        self.assertEqual(cat, "revisar_manual")
        self.assertIn("documento", motivo)

    def test_clip_sexual_muy_seguro_es_explicito_sin_nudenet(self) -> None:
        self.assertEqual(pulir_fotos.decidir([], probs(explicito=0.9), "a.jpg")[0], "explicito")

    def test_no_fotos_van_a_revisar(self) -> None:
        for cat_clip, texto in (("documento", "documento"), ("captura", "captura"), ("tapa_disco", "tapa")):
            cat, motivo = pulir_fotos.decidir([], probs(**{cat_clip: 0.8}), "a.jpg")
            self.assertEqual(cat, "revisar_manual")
            self.assertIn(texto, motivo)

    def test_meme_pide_mas_seguridad(self) -> None:
        self.assertEqual(pulir_fotos.decidir([], probs(meme_dibujo=0.6, foto=0.3), "a.jpg")[0], "no_explicito")
        self.assertEqual(pulir_fotos.decidir([], probs(meme_dibujo=0.8), "a.jpg")[0], "revisar_manual")

    def test_casi_nada_de_foto_se_marca(self) -> None:
        cat, _ = pulir_fotos.decidir([], probs(foto=0.02, meme_dibujo=0.5, documento=0.4), "a.png")
        self.assertEqual(cat, "revisar_manual")

    def test_nombre_de_captura(self) -> None:
        self.assertEqual(pulir_fotos.decidir([], probs(foto=0.9), "Captura de pantalla 2024.png")[0], "revisar_manual")


class AnalizadorFalso:
    """Decide por el nombre del archivo, sin cargar modelos."""

    def __init__(self) -> None:
        self.rutas: list[str] = []

    def analizar(self, imagenes):
        salida = []
        for img in imagenes:
            nombre = img.info.get("nombre", "")
            if "porno" in nombre:
                salida.append(([nn("FEMALE_GENITALIA_EXPOSED", 0.9)], probs(foto=0.1)))
            elif "factura" in nombre:
                salida.append(([], probs(documento=0.9)))
            else:
                salida.append(([], probs(foto=0.95)))
        return salida


class PulidoPuntaAPuntaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def crear(self, rel: str) -> None:
        ruta = self.root / "Todas" / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 24), (90, 90, 90)).save(ruta)

    def correr(self) -> None:
        cargar_real = pulir_fotos.cargar_imagen

        def cargar(ruta: Path):
            img = cargar_real(ruta)
            if img is not None:
                img.info["nombre"] = ruta.name
            return img

        with mock.patch.object(pulir_fotos, "Analizador", AnalizadorFalso), \
                mock.patch.object(pulir_fotos, "cargar_imagen", cargar), \
                mock.patch.object(sys, "argv", ["pulir_fotos.py", str(self.root / "Todas")]), \
                mock.patch("builtins.input", return_value="s"), \
                mock.patch.object(pulir_fotos, "aviso_destino_tinder", lambda _: None), \
                mock.patch("sys.stdout"):
            pulir_fotos.main()

    def test_respeta_subcarpetas_guarda_motivos_y_el_tinder_lo_lee(self) -> None:
        self.crear("pendrive/Camara/2024/2024-07/playa.jpg")
        self.crear("pendrive/Camara/2024/2024-07/porno.jpg")
        self.crear("disco/Cámara vieja/factura.png")
        roto = self.root / "Todas" / "roto.jpg"
        roto.write_text("no soy una imagen")
        self.correr()

        pulido = self.root / "Todas_pulido"
        self.assertTrue((pulido / "no_explicito/pendrive/Camara/2024/2024-07/playa.jpg").exists())
        self.assertTrue((pulido / "explicito/pendrive/Camara/2024/2024-07/porno.jpg").exists())
        self.assertTrue((pulido / "revisar_manual/disco/Cámara vieja/factura.png").exists())
        self.assertTrue(roto.exists(), "las que no se pueden abrir quedan en el origen")
        motivos = json.loads((pulido / pulir_fotos.ARCHIVO_MOTIVOS).read_text(encoding="utf-8"))
        self.assertEqual(set(motivos), {
            "explicito/pendrive/Camara/2024/2024-07/porno.jpg",
            "revisar_manual/disco/Cámara vieja/factura.png",
        })

        # El Tinder reconoce el _pulido (también eligiendo la carpeta original) y muestra el motivo.
        sesion = webapp.Sesion(destino=self.root / "FotosFinales", persistir=False)
        sesion.set_destino(str(self.root / "FotosFinales"))
        info = sesion.inspeccionar(str(self.root / "Todas"))
        self.assertEqual(Path(info["root"]), pulido.resolve())
        self.assertEqual(info["pendientes"], 2)
        estado = sesion.set_origen(str(pulido), pasar_normales=True)
        metas = [estado["foto"], *estado["siguientes"]]
        por_nombre = {m["nombre"]: m for m in metas}
        self.assertIn("documento", por_nombre["factura.png"]["motivo"])
        self.assertIn("NudeNet", por_nombre["porno.jpg"]["motivo"])
        self.assertEqual(por_nombre["porno.jpg"]["lote"], "Todas")
        self.assertTrue((self.root / "FotosFinales/normales/Todas/pendrive/Camara/2024/2024-07/playa.jpg").exists())

    def test_se_puede_retomar_si_se_corta(self) -> None:
        self.crear("a/factura.jpg")
        self.correr()
        self.crear("b/factura.jpg")
        self.correr()
        motivos = json.loads((self.root / "Todas_pulido" / pulir_fotos.ARCHIVO_MOTIVOS).read_text(encoding="utf-8"))
        self.assertEqual(set(motivos), {"revisar_manual/a/factura.jpg", "revisar_manual/b/factura.jpg"})


if __name__ == "__main__":
    unittest.main()
