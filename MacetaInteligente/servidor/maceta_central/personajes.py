"""Personaje (aspecto) de cada maceta. Solo cambia cómo se ve: los datos y las reglas son los mismos.
Para agregar uno: carpeta web/personajes/<id>/ con los 7 estados y mini .webp, y una línea en catalogo.json.
Con "capas": true, capas.json dice qué piezas se animan (ojo, boca, copa, par, cae, gira, zz)."""
import json
from pathlib import Path

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

CARPETA = Path(__file__).parent / "web" / "personajes"
ESTADOS = ("sed", "enc", "poca", "mucha", "feliz", "estr", "off")
NORMAL = "maceta"
ESQUEMA = "CREATE TABLE IF NOT EXISTS personajes(maceta_id TEXT PRIMARY KEY REFERENCES macetas(id), personaje TEXT NOT NULL)"


class Eleccion(BaseModel):
    personaje: str = Field(max_length=40)


def catalogo():
    return json.loads((CARPETA / "catalogo.json").read_text(encoding="utf-8"))


def validar(p):
    if p not in {x["id"] for x in catalogo()}:
        raise HTTPException(422, "No existe ese personaje")


def poner(base, mid, p):
    with base.con() as c:
        c.execute("INSERT INTO personajes VALUES(?,?) ON CONFLICT(maceta_id) DO UPDATE SET personaje=excluded.personaje", (mid, p))


def registrar(app, bases, buscar, permitido):
    for b in bases:
        with b.con() as c:
            c.execute(ESQUEMA)
        b.tablas_extra += ("personajes",)   # para borrar_maceta

    @app.get("/api/v1/personajes")
    def ver():
        asignados = {}
        for b in bases:
            with b.con() as c:
                asignados.update(tuple(f) for f in c.execute("SELECT maceta_id,personaje FROM personajes"))
        return {"catalogo": catalogo(), "asignados": asignados}

    @app.put("/api/v1/macetas/{mid}/personaje", dependencies=[Depends(permitido)])
    def cambiar(mid: str, e: Eleccion):
        validar(e.personaje)
        poner(buscar(mid)[0], mid, e.personaje)
        return {"ok": True}
