"""Cuatro macetas virtuales para la presentación.
Escribe 1-4 y Enter para apagar o encender una; s para salir.

python -m simulador.demo      (con el servidor abierto: python -m maceta_central --demo)"""
import argparse
import json
import sys
import threading
import urllib.error
import urllib.request

from .maceta_virtual import servidor

VIRTUALES = [("Virtual sana", "sana", 8101), ("Virtual con sed", "sed", 8102),
             ("Virtual encharcada", "encharcada", 8103), ("Virtual con poca luz", "poca_luz", 8104)]


def encender(escenario, puerto):
    s = servidor(puerto, escenario)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def apagar(s):
    s.shutdown()
    s.server_close()


def registrar(central, nombre, puerto):
    """Devuelve True si quedó registrada (o ya lo estaba)."""
    p = urllib.request.Request(central + "/api/v1/macetas", headers={"X-Maceta": "1", "Content-Type": "application/json"},
                               data=json.dumps({"nombre": nombre, "url": f"127.0.0.1:{puerto}", "origen": "simulado"}).encode())
    try:
        urllib.request.build_opener(urllib.request.ProxyHandler({})).open(p, timeout=10).close()
        return True
    except urllib.error.HTTPError as e:
        e.close()
        return e.code == 409
    except OSError:
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--central", default="http://127.0.0.1:8000")
    a = p.parse_args()
    activas = {}
    for i, (nombre, esc, puerto) in enumerate(VIRTUALES, 1):
        activas[i] = encender(esc, puerto)
        if not registrar(a.central, nombre, puerto):
            print(f"No se registró «{nombre}»: abre antes el servidor con --demo")
    print("Macetas SIMULADAS encendidas. 1-4: apagar o encender. s: salir.", flush=True)
    for linea in sys.stdin:
        t = linea.strip().lower()
        if t == "s":
            break
        if t in ("1", "2", "3", "4"):
            i = int(t)
            nombre, esc, puerto = VIRTUALES[i - 1]
            if activas.get(i):
                apagar(activas.pop(i))
                print(f"{nombre}: apagada (el dashboard lo muestra en unos 30 s)", flush=True)
            else:
                activas[i] = encender(esc, puerto)
                print(f"{nombre}: encendida", flush=True)
    for s in activas.values():
        apagar(s)


if __name__ == "__main__":
    main()
