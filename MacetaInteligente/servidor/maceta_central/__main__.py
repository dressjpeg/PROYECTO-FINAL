"""python -m maceta_central [--simulado] [--puerto 8000]"""
import argparse
import logging
from pathlib import Path

import uvicorn

from .app import crear_app
from .base import Base

p = argparse.ArgumentParser()
p.add_argument("--simulado", action="store_true", help="usa una base aparte, solo para macetas virtuales")
p.add_argument("--puerto", type=int, default=8000)
p.add_argument("--datos", default=str(Path(__file__).resolve().parent.parent / "datos"))
a = p.parse_args()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
tipo = "simulado" if a.simulado else "real"
# Solo este PC: abrirlo a la red exige primero una contraseña
uvicorn.run(crear_app(Base(Path(a.datos) / f"{tipo}.db", tipo)), host="127.0.0.1", port=a.puerto, log_level="warning")
