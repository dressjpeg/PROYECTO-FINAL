"""Mide cuántas macetas atiende el servidor en este PC (no mide el WiFi).
Aprueba un nivel si todas cargan su historial, siguen conectadas y el p95 de consulta es < 5 s.

python -m simulador.prueba_carga"""
import argparse
import json
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from maceta_central.base import Base
from maceta_central.ingesta import Ingesta

from .maceta_virtual import servidor

PUERTO = 21000
LIMITE_S = 5


def flota(n):
    for i in range(n):
        s = servidor(PUERTO + i)
        threading.Thread(target=s.serve_forever, daemon=True).start()
    print("lista", flush=True)
    sys.stdin.read()


def nivel(n, espera):
    p = subprocess.Popen([sys.executable, "-m", "simulador.prueba_carga", "--flota", str(n)], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, text=True)
    try:
        if p.stdout.readline().strip() != "lista":
            raise RuntimeError("No se pudieron abrir las macetas simuladas")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            b = Base(Path(d) / "carga.db", "simulado")
            for i in range(n):
                b.crear_maceta(f"c{i}", f"http://127.0.0.1:{PUERTO + i}")
            ing = Ingesta(b)
            t = time.monotonic()
            ing.sincronizar()
            vs = list(ing.vigilantes.values())
            while time.monotonic() - t < 120 and not all(v.t_hist for v in vs):
                time.sleep(.2)
            carga = time.monotonic() - t
            for v in vs:
                v.latencias.clear()
            time.sleep(espera)
            lat = sorted(x for v in vs for x in v.latencias)
            p95 = lat[int(len(lat) * .95)] if lat else None
            con = sum(v.conectada for v in vs)
            historial = sum(v.t_hist is not None for v in vs)
            completas = sum(m["lecturas"] >= 2016 for m in b.macetas())
            ing.parar.set()
            time.sleep(1)
        return {"macetas": n, "conectadas": con, "con_historial": historial, "completas": completas, "carga_inicial_s": round(carga, 1),
                "p95_s": p95 and round(p95, 3), "ok": con == historial == completas == n and bool(p95) and p95 < LIMITE_S}
    finally:
        p.stdin.close()
        p.wait(10)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--flota", type=int)
    a.add_argument("--niveles", default="10,20,40,80")
    a.add_argument("--espera", type=float, default=35)
    a.add_argument("--salida", default=str(Path(__file__).resolve().parent.parent / "datos" / "carga.json"))
    a = a.parse_args()
    if a.flota:
        return flota(a.flota)
    res = []
    for n in map(int, a.niveles.split(",")):
        res.append(nivel(n, a.espera))
        print(res[-1], flush=True)
        if not res[-1]["ok"]:
            break
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.salida).write_text(json.dumps({"fecha": int(time.time()), "niveles": res}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
