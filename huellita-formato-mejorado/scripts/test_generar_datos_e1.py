"""Pruebas del generador de la rúbrica 5 × 9 y de la semilla local (solo biblioteca estándar).

Uso (PowerShell, desde huellita-formato-mejorado):
  python -m unittest discover -s scripts -p "test_*.py"
"""
from __future__ import annotations

import json
import re
import unittest

import generar_datos_e1 as g


class PruebasRubrica(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rubrica = g.generar_rubrica()

    def test_nueve_niveles_contiguos_desde_cero(self) -> None:
        niveles = self.rubrica["niveles"]
        self.assertEqual([n["nivel"] for n in niveles], list(range(1, 10)))
        tramos = [tuple(int(x) for x in re.findall(r"\d+", n["edad_orientativa"])) for n in niveles]
        self.assertEqual(tramos[0][0], 0)
        self.assertEqual(tramos[-1], (27, 36))
        for (_, hasta), (desde, _) in zip(tramos, tramos[1:]):
            self.assertEqual(hasta, desde)

    def test_cinco_dominios_con_dos_conductas_por_celda(self) -> None:
        codigos = [d["codigo"] for d in self.rubrica["rubrica"]]
        self.assertEqual(
            codigos, ["motor_grueso", "motor_fino", "lenguaje_comunicacion", "socioemocional", "cognitivo"]
        )
        for dominio in self.rubrica["rubrica"]:
            self.assertEqual(len(dominio["niveles"]), 9)
            for celda in dominio["niveles"]:
                self.assertEqual(len(celda["conductas_observables"]), 2)
                self.assertTrue(celda["descriptor"])

    def test_los_archivos_versionados_estan_al_dia(self) -> None:
        guardada = json.loads((g.SALIDA / "rubrica_e1.json").read_text(encoding="utf-8"))
        self.assertEqual(guardada, self.rubrica)


class PruebasSemilla(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.semilla = g.generar_semilla()
        rubrica = g.generar_rubrica()
        cls.conductas = {
            (d["codigo"], c["nivel"]): c["conductas_observables"] for d in rubrica["rubrica"] for c in d["niveles"]
        }

    def test_26_ninos_con_nombre_13_por_sala(self) -> None:
        ninos = self.semilla["ninos"]
        self.assertEqual(len(ninos), 26)
        for sala in g.SALAS:
            self.assertEqual(sum(1 for n in ninos if n["salaId"] == sala), 13)
        self.assertTrue(all(n["nombre"] and n["activo"] for n in ninos))
        martinas = [(n["nombre"], n["apellidoInicial"]) for n in ninos if n["nombre"] == "Martina"]
        self.assertEqual(martinas, [("Martina", "M."), ("Martina", "R.")])

    def test_historial_completo_de_esos_ninos(self) -> None:
        ids = {n["id"] for n in self.semilla["ninos"]}
        esperadas = {o["id_observacion"] for o in g.leer_csv("observaciones.csv") if o["id_nino"] in ids}
        historial = {e["id"] for e in self.semilla["evidencias"] if e["id"].startswith("OBS-")}
        self.assertEqual(historial, esperadas)
        self.assertEqual(len(historial), 155)

    def test_una_sugerencia_aceptada_por_dominio_de_cada_observacion(self) -> None:
        dominios_por_obs: dict[str, set[str]] = {}
        cruce = {m["id_manifestacion"]: m["dominio"] for m in g.leer_csv("manifestaciones.csv")}
        for fila in g.leer_csv("observacion_manifestaciones.csv"):
            dominios_por_obs.setdefault(fila["id_observacion"], set()).add(cruce[fila["id_manifestacion"]])
        for e in self.semilla["evidencias"]:
            if not e["id"].startswith("OBS-"):
                continue
            suyas = [s for s in self.semilla["sugerencias"] if s["evidenciaId"] == e["id"]]
            self.assertEqual({s["nucleo"] for s in suyas}, dominios_por_obs[e["id"]])
            self.assertTrue(all(s["estado"] == "aceptada" and s["validadaPor"] == e["autorId"] for s in suyas))

    def test_dominios_niveles_y_conductas_validos(self) -> None:
        for s in self.semilla["sugerencias"]:
            if s["tipo"] != "evaluacion":
                continue
            self.assertIn(s["nivel"], range(1, 10))
            self.assertIn(s["conducta"], self.conductas[(s["nucleo"], s["nivel"])])
        for guion in self.semilla["demoCapturas"]:
            for s in guion["sugerencias"]:
                if s["tipo"] == "evaluacion":
                    self.assertIn(s["conducta"], self.conductas[(s["nucleo"], s["nivel"])])

    def test_demo_de_hoy_con_tres_pendientes_de_la_sala_a(self) -> None:
        pendientes = [s for s in self.semilla["sugerencias"] if s["estado"] == "pendiente"]
        self.assertEqual(len(pendientes), 3)
        self.assertTrue(all(s["salaId"] == "SG-A" for s in pendientes))

    def test_tias_de_las_educadoras_reales_y_una_directora_local(self) -> None:
        usuarias = {u["id"]: u for u in self.semilla["usuarias"]}
        self.assertEqual(set(usuarias), {"EDU-0001", "EDU-0002", "USR-CARMEN"})
        self.assertEqual(usuarias["USR-CARMEN"]["rol"], "directora")

    def test_los_archivos_versionados_estan_al_dia(self) -> None:
        guardada = json.loads((g.SALIDA / "semilla.json").read_text(encoding="utf-8"))
        self.assertEqual(guardada, self.semilla)


class PruebasReglas(unittest.TestCase):
    def test_separa_la_inicial_de_los_homonimos(self) -> None:
        self.assertEqual(g.separar_nombre("Martina M."), ("Martina", "M."))
        self.assertEqual(g.separar_nombre("Nayara"), ("Nayara", ""))

    def test_nivel_educativo_por_mediana_de_edad(self) -> None:
        self.assertEqual(g.nivel_educativo(11), "Sala Cuna Menor")
        self.assertEqual(g.nivel_educativo(24), "Medio Menor")
        self.assertEqual(g.nivel_educativo(60), "Transición 2")
        self.assertEqual(g.mediana_baja([5, 20, 24, 40]), 20)

    def test_texto_literal_como_integra_procesador(self) -> None:
        mans = [{"texto_observable": "Uno."}, {"texto_observable": "Dos."}]
        self.assertEqual(g.texto_literal(mans, "  Nota.  "), "Uno. Dos. Nota.")
        self.assertEqual(g.texto_literal(mans, ""), "Uno. Dos.")


if __name__ == "__main__":
    unittest.main()
