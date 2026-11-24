"""python -m maceta_central [--demo] [--red [--codigo]] [--puerto 8000]"""
import argparse
import logging
import socket
import threading
from pathlib import Path

import uvicorn

from .acceso import Acceso, direccion_red
from .app import crear_app
from .base import Base
from .certificado import obtener

p = argparse.ArgumentParser()
p.add_argument("--demo", action="store_true", help="agrega macetas simuladas, con base aparte")
p.add_argument("--red", action="store_true", help="permite entrar desde el celular, sin código: solo en una red privada")
p.add_argument("--codigo", action="store_true", help="con --red: HTTPS y código de un solo uso")
p.add_argument("--puerto", type=int, default=8000)
p.add_argument("--puerto-red", type=int, default=8443)
p.add_argument("--datos", default=str(Path(__file__).resolve().parent.parent / "datos"))
a = p.parse_args()
if a.codigo and not a.red:
    p.error("--codigo va junto con --red")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
bases = [Base(Path(a.datos) / f"{t}.db", t) for t in (("real", "simulado") if a.demo else ("real",))]
print(f"Dashboard central: http://127.0.0.1:{a.puerto}", flush=True)
acceso = None
if a.codigo:
    cert, clave, huella = obtener()
    acceso = Acceso(a.puerto_red, huella_tls=huella)
elif a.red:
    acceso = Acceso(a.puerto, con_codigo=False)
app = crear_app(*bases, acceso=acceso)
# Sin proxy_headers nadie puede fingir su IP
comun = dict(log_level="warning", proxy_headers=False, server_header=False)
if a.codigo:
    # La red solo entra por HTTPS; el HTTP de abajo sigue siendo exclusivo de este PC
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", a.puerto_red))
    https = uvicorn.Server(uvicorn.Config(app, ssl_certfile=cert, ssl_keyfile=clave, lifespan="off", limit_concurrency=100, **comun))
    threading.Thread(target=https.run, kwargs={"sockets": [s]}, daemon=True).start()
    print(f"Desde el celular: https://{direccion_red() or 'IP-de-este-PC'}:{a.puerto_red}  (crea el código en el dashboard del PC)", flush=True)
elif a.red:
    print(f"Desde el celular: http://{direccion_red() or 'IP-de-este-PC'}:{a.puerto}  (sin código: solo en una red privada)", flush=True)
uvicorn.run(app, host="0.0.0.0" if a.red and not a.codigo else "127.0.0.1", port=a.puerto, **comun)
