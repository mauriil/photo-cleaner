#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import webapp


def crear_foto(ruta: Path, color: tuple[int, int, int]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 24), color).save(ruta)


def arbol_clasificado(raiz: Path, **categorias: list[str]) -> Path:
    """Simula la carpeta que deja clasificar_fotos.py."""
    clasificado = raiz if raiz.name.endswith("_clasificado") else raiz.parent / f"{raiz.name}_clasificado"
    for categoria, nombres in categorias.items():
        for nombre in nombres:
            crear_foto(clasificado / categoria / "Camara" / "2024" / "2024-01" / nombre, (80, 80, 80))
    for categoria in webapp.CARPETAS_CONSOLA:
        (clasificado / categoria).mkdir(parents=True, exist_ok=True)
    return clasificado


class PostConsolaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.destino = self.root / "cumulo"
        self.sesion = webapp.Sesion(destino=self.destino, persistir=False)
        self.sesion.set_destino(str(self.destino))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_solo_revisa_explicito_y_revisar_manual(self) -> None:
        clasificado = arbol_clasificado(
            self.root / "usb",
            explicito=["borrar.jpg"],
            no_explicito=["ya_ok.jpg"],
            revisar_manual=["duda.jpg"],
        )
        estado = self.sesion.set_origen(str(clasificado), pasar_normales=False)
        nombres = [p.name for p in self.sesion_fotos()]
        self.assertEqual(sorted(nombres), ["borrar.jpg", "duda.jpg"])
        self.assertEqual(estado["total"], 2)
        self.assertTrue((clasificado / "no_explicito" / "Camara" / "2024" / "2024-01" / "ya_ok.jpg").exists())

    def test_detecta_la_carpeta_vecina_clasificado(self) -> None:
        origen = self.root / "Vacaciones"
        origen.mkdir()
        clasificado = arbol_clasificado(
            origen,
            explicito=["nuda.jpg"],
            no_explicito=[],
            revisar_manual=[],
        )
        info = self.sesion.inspeccionar(str(origen))
        self.assertEqual(Path(info["root"]), clasificado.resolve())
        self.assertEqual(info["pendientes"], 1)

    def test_acumula_varios_resultados_de_consola_en_tres_carpetas(self) -> None:
        lote_a = arbol_clasificado(
            self.root / "pendrive",
            explicito=["exp_a.jpg"],
            no_explicito=["ok_a.jpg"],
            revisar_manual=["duda_a.jpg"],
        )
        lote_b = arbol_clasificado(
            self.root / "disco",
            explicito=["exp_b.jpg"],
            no_explicito=["ok_b.jpg"],
            revisar_manual=[],
        )

        self.sesion.set_origen(str(lote_a), pasar_normales=True)
        while self.sesion.actual():
            nombre = self.sesion.actual().name
            if nombre.startswith("duda"):
                self.sesion.aplicar("normales")
            else:
                self.sesion.aplicar("explicitas_borrar")

        self.sesion.set_origen(str(lote_b), pasar_normales=True)
        self.sesion.aplicar("explicitas_guardar")

        self.assertEqual(self.sesion.conteos(), {
            "normales": 3,
            "explicitas_guardar": 1,
            "explicitas_borrar": 1,
        })
        sub = Path("Camara") / "2024" / "2024-01"
        self.assertTrue((self.destino / "normales" / "pendrive" / sub / "ok_a.jpg").exists())
        self.assertTrue((self.destino / "normales" / "disco" / sub / "ok_b.jpg").exists())
        self.assertTrue((self.destino / "normales" / "pendrive" / sub / "duda_a.jpg").exists())
        self.assertTrue((self.destino / "explicitas_guardar" / "disco" / sub / "exp_b.jpg").exists())
        self.assertTrue((self.destino / "explicitas_borrar" / "pendrive" / sub / "exp_a.jpg").exists())

    def test_deshacer_devuelve_la_foto_al_clasificado(self) -> None:
        clasificado = arbol_clasificado(
            self.root / "inbox",
            explicito=["unica.jpg"],
            no_explicito=[],
            revisar_manual=[],
        )
        original = clasificado / "explicito" / "Camara" / "2024" / "2024-01" / "unica.jpg"
        self.sesion.set_origen(str(clasificado))
        self.sesion.aplicar("explicitas_guardar")
        self.assertFalse(original.exists())
        self.sesion.deshacer_ultima()
        self.assertTrue(original.exists())
        self.assertEqual(self.sesion.actual().name, "unica.jpg")
        self.assertEqual(self.sesion.conteos()["explicitas_guardar"], 0)

    def test_rechaza_una_carpeta_que_no_vino_de_la_consola(self) -> None:
        suelta = self.root / "fotos_crudas"
        crear_foto(suelta / "a.jpg", (1, 1, 1))
        with self.assertRaises(ValueError):
            self.sesion.set_origen(str(suelta))

    def test_filtra_si_eligio_solo_revisar_manual(self) -> None:
        clasificado = arbol_clasificado(
            self.root / "lote",
            explicito=["exp.jpg"],
            no_explicito=["ok.jpg"],
            revisar_manual=["duda.jpg"],
        )
        self.sesion.set_origen(str(clasificado / "revisar_manual"))
        self.assertEqual([p.name for p in self.sesion_fotos()], ["duda.jpg"])

    def test_carpeta_madre_con_varios_lotes_arma_una_sola_cola(self) -> None:
        madre = self.root / "todas"
        arbol_clasificado(madre / "pendrive", explicito=["a.jpg"], no_explicito=["ok.jpg"], revisar_manual=[])
        arbol_clasificado(madre / "2023" / "disco", explicito=[], no_explicito=[], revisar_manual=["b.jpg"])
        info = self.sesion.inspeccionar(str(madre))
        self.assertEqual(info["pendientes"], 2)
        self.assertEqual(sorted(l["etiqueta"] for l in info["lotes"]), ["2023/disco", "pendrive"])

        self.sesion.set_origen(str(madre), pasar_normales=True)
        self.assertEqual(sorted(p.name for p in self.sesion_fotos()), ["a.jpg", "b.jpg"])
        while self.sesion.actual():
            self.sesion.aplicar("explicitas_guardar")
        sub = Path("Camara") / "2024" / "2024-01"
        self.assertTrue((self.destino / "explicitas_guardar" / "pendrive" / sub / "a.jpg").exists())
        self.assertTrue((self.destino / "explicitas_guardar" / "2023" / "disco" / sub / "b.jpg").exists())
        self.assertTrue((self.destino / "normales" / "pendrive" / sub / "ok.jpg").exists())

    def test_acepta_nombres_en_ingles(self) -> None:
        lote = self.root / "fotos"
        crear_foto(lote / "explicit" / "x.jpg", (1, 1, 1))
        crear_foto(lote / "Non-Explicit" / "ok.jpg", (2, 2, 2))
        crear_foto(lote / "force revisit" / "y.jpg", (3, 3, 3))
        info = self.sesion.inspeccionar(str(lote))
        self.assertEqual(info["conteos_consola"], {"explicito": 1, "no_explicito": 1, "revisar_manual": 1})
        self.sesion.set_origen(str(lote))
        cats = {self.sesion.cola[i].foto.name: self.sesion.cola[i].categoria for i in range(len(self.sesion.cola))}
        self.assertEqual(cats, {"x.jpg": "explicito", "y.jpg": "revisar_manual"})

    def test_elegir_una_categoria_en_ingles_filtra(self) -> None:
        lote = self.root / "fotos"
        crear_foto(lote / "explicit" / "x.jpg", (1, 1, 1))
        crear_foto(lote / "force-revisit" / "y.jpg", (3, 3, 3))
        self.sesion.set_origen(str(lote / "force-revisit"))
        self.assertEqual([p.name for p in self.sesion_fotos()], ["y.jpg"])

    def test_no_escanea_el_destino_aunque_este_adentro(self) -> None:
        madre = self.root / "todas"
        arbol_clasificado(madre / "lote", explicito=["a.jpg"], no_explicito=[], revisar_manual=[])
        destino = madre / "cumulo"
        self.sesion.set_destino(str(destino))
        crear_foto(destino / "normales" / "viejo" / "explicito" / "z.jpg", (4, 4, 4))
        self.sesion.set_origen(str(madre))
        self.assertEqual([p.name for p in self.sesion_fotos()], ["a.jpg"])

    def test_deshacer_con_estructura_y_conteos(self) -> None:
        lote = arbol_clasificado(self.root / "lote", explicito=["a.jpg", "b.jpg"], no_explicito=[], revisar_manual=[])
        self.sesion.set_origen(str(lote))
        primero = self.sesion.cola[0].foto
        estado = self.sesion.aplicar("explicitas_borrar")
        self.assertEqual(estado["conteos"]["explicitas_borrar"], 1)
        self.assertEqual(len(estado["siguientes"]), 0)
        estado = self.sesion.deshacer_ultima()
        self.assertTrue(primero.exists())
        self.assertEqual(estado["conteos"]["explicitas_borrar"], 0)
        self.assertEqual(estado["foto"]["preview"], f"/api/preview/{self.sesion.cola[0].id}")

    def sesion_fotos(self) -> list[Path]:
        return [it.foto for it in self.sesion.cola]


if __name__ == "__main__":
    unittest.main()
