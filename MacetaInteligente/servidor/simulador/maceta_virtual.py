"""Maceta virtual: responde como el ESP32 (GET de estado, config, historial y diario).
Todo lo que entrega es SIMULADO y lo marca con "simulada": true."""
import argparse
import json
import math
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ESCENARIOS = {"sana": (55, 55), "sed": (18, 55), "encharcada": (93, 55), "poca_luz": (55, 8)}
TEXTO = ["Sed", "Encharcada", "Poca luz", "Mucha luz", "Feliz", "Estresada"]
CLAVE = ["SED", "ENCHARCADA", "POCA_LUZ", "MUCHA_LUZ", "FELIZ", "ESTRESADA"]
FRASE = ["Me muero de sed!", "Me ahogo! Basta!", "Esta muy oscuro!", "Me quemo al sol!", "Soy muy feliz!!", "Me siento mal..."]
CAMPOS = ["t", "hora", "hum_pct", "luz_pct", "indice", "estado", "hum_raw", "luz_raw", "arranque"]
CAMPOS_DIA = ["fecha", "hum_prom", "hum_min", "hum_max", "luz_prom", "luz_min", "luz_max", "indice_prom", "riegos",
              "min_sed", "min_encharcada", "min_poca_luz", "min_mucha_luz", "min_estresada", "muestras"]
RANGOS = {"1h": 3600, "24h": 86400, "7d": 604800}
PASO = 300


class Simulacion:
    def __init__(self, escenario="sana"):
        self.hum, self.luz = ESCENARIOS[escenario]
        self.inicio = int(time.time()) - 7 * 86400

    def lectura(self, t):
        """Determinista: la misma hora siempre da la misma lectura."""
        h = max(0, min(100, round(self.hum + 3 * math.sin(t / 5000))))
        l = max(0, min(100, round(self.luz + 5 * math.sin(t / 3000))))
        hr = round(4095 + (1620 - 4095) * h / 100)                     # inverso de aPorcentaje()
        oscuro, claro = 4000 / 95, 30 / 4065                           # inverso de luzPorcentajeLog()
        rel = oscuro / math.exp(l / 100 * math.log(oscuro / claro))
        ph = h * 100 // 40 if h < 40 else (100 - h) * 100 // 25 if h > 75 else 100
        pl = l * 100 // 30 if l < 30 else (100 - l) * 100 // 20 if l > 80 else 100
        ind = (50 * ph + 30 * pl + 2000) // 100
        av = [e for e, si in enumerate((h < 30, h > 85, l < 20, l > 90)) if si]
        return {"h": h, "l": l, "hr": hr, "lr": round(4095 * rel / (1 + rel)), "i": ind, "av": av or [5 if ind < 70 else 4]}

    def estado(self):
        t = int(time.time())
        x, up = self.lectura(t), t - self.inicio
        e = x["av"][0]

        def item(k):
            return {"estado": k, "clave": CLAVE[k], "texto": TEXTO[k]}
        av = [k for k in x["av"] if k != 4]
        return {"simulada": True, "listo": True, "uptime_s": up, "hum_raw": x["hr"], "luz_raw": x["lr"], "hum_pct": x["h"],
                "luz_pct": x["l"], "indice": x["i"], "estado": e, "estado_texto": TEXTO[e], "frase": FRASE[e],
                "horas_sin_regar": 12, "avisos": [{**item(k), "frase": FRASE[k]} for k in av],
                "alertas": [{**item(k), "desde_s": 3600, "inicio": t - 3600} for k in av], "resueltas": [],
                "wifi_rssi": -55, "ip": "127.0.0.1", "hora_real": True, "epoch": t, "fs_ok": True, "fs_usado": 60000,
                "fs_total": 1441792, "heap_libre": 180000, "heap_min": 150000, "arranque": 1, "estados": x["av"], "pers": 0,
                # Sensores futuros (BH1750 y SHT31): solo existen en las virtuales
                "luz_lx": round(10 ** (x["l"] / 20)), "temp_c": round(23 + 3 * math.sin(t / 9000), 1)}

    def config(self):
        return {"simulada": True,
                "umbrales": {"sed": 30, "encharcada": 85, "poca_luz": 20, "mucha_luz": 90, "estres": 70, "salto_riego": 15},
                "calibracion": {"hum_seco": 4095, "hum_humedo": 1620, "luz_oscuro_log": 4000, "luz_claro_log": 30,
                                "luz_escala": "logaritmica"},
                "tiempos": {"muestra_ms": 1000, "confirmar_ms": 5000, "riego_ms": 10000, "ms_por_hora": 3600000,
                            "historial_ms": 300000, "alerta_agua_min": 10, "alerta_otras_min": 30}, "personalidad": 0}

    def historial(self, rango):
        t = int(time.time())
        datos = []
        for s in range((t - RANGOS[rango]) // PASO * PASO + PASO, t + 1, PASO):
            x = self.lectura(s)
            datos.append([s, 1, x["h"], x["l"], x["i"], x["av"][0], x["hr"], x["lr"], 1])
        return {"hora_real": True, "ahora": t, "uptime_s": t - self.inicio, "arranque": 1, "campos": CAMPOS, "datos": datos}

    def diario(self):
        dias, hoy = [], int(time.time())
        for k in range(6, 0, -1):
            f = time.strftime("%Y-%m-%d", time.localtime(hoy - k * 86400))
            ini = int(time.mktime(time.strptime(f, "%Y-%m-%d")))
            m = [self.lectura(s) for s in range(ini, ini + 86400, PASO)]

            def g(c):
                return [x[c] for x in m]

            def prom(c):
                return round(sum(g(c)) / len(m), 1)

            def est(e):
                return sum(e in x["av"] for x in m) * PASO // 60
            dias.append([f, prom("h"), min(g("h")), max(g("h")), prom("l"), min(g("l")), max(g("l")), prom("i"), 0,
                         est(0), est(1), est(2), est(3), est(5), len(m)])
        return {"campos": CAMPOS_DIA, "dias": dias, "hoy_parcial": None}


def servidor(puerto, escenario="sana"):
    sim = Simulacion(escenario)

    class Peticion(BaseHTTPRequestHandler):
        def do_GET(self):
            u = urlsplit(self.path)
            rango = parse_qs(u.query).get("rango", ["1h"])[0]
            rutas = {"/api/estado": sim.estado, "/api/config": sim.config, "/api/diario": sim.diario}
            if u.path in rutas:
                self.responder(200, rutas[u.path]())
            elif u.path == "/api/historial" and rango in RANGOS:
                self.responder(200, sim.historial(rango))
            elif u.path == "/api/historial":
                self.responder(400, {"ok": False, "error": "rango debe ser 1h, 24h o 7d"})
            else:
                self.responder(404, {"ok": False, "error": "Ruta no encontrada"})

        def responder(self, codigo, d):
            b = json.dumps(d).encode()
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def log_message(self, *a):
            pass

    return ThreadingHTTPServer(("127.0.0.1", puerto), Peticion)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--puerto", type=int, default=8101)
    p.add_argument("--escenario", choices=ESCENARIOS, default="sana")
    a = p.parse_args()
    print(f"Maceta SIMULADA ({a.escenario}) en http://127.0.0.1:{a.puerto}", flush=True)
    servidor(a.puerto, a.escenario).serve_forever()
