"""python -m maceta_central [--demo] [--puerto 8000]"""
import argparse
import logging
from pathlib import Path

import uvicorn

from .app import crear_app
from .base import Base

p = argparse.ArgumentParser()
p.add_argument("--demo", action="store_true", help="agrega macetas simuladas, con base aparte")
p.add_argument("--puerto", type=int, default=8000)
p.add_argument("--datos", default=str(Path(__file__).resolve().parent.parent / "datos"))
a = p.parse_args()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
bases = [Base(Path(a.datos) / f"{t}.db", t) for t in (("real", "simulado") if a.demo else ("real",))]
print(f"Dashboard central: http://127.0.0.1:{a.puerto}", flush=True)
# Solo este PC: abrirlo a la red exige primero una contraseña
uvicorn.run(crear_app(*bases), host="127.0.0.1", port=a.puerto, log_level="warning")
