"""API del servidor central."""
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from .adaptador_http import validar_url
from .base import Conflicto
from .ingesta import Ingesta


class Direccion(BaseModel):
    url: str = Field(max_length=200)

    @field_validator("url")
    @classmethod
    def _url(cls, v):
        return validar_url(v)


class NuevaMaceta(Direccion):
    nombre: str = Field(min_length=1, max_length=60)
    especie: str = Field("", max_length=80)

    @field_validator("nombre", "especie", mode="before")
    @classmethod
    def _limpio(cls, v):
        return v.strip() if isinstance(v, str) else v


def permitido(x_maceta: str = Header("")):
    # Impide que otra web abierta en el navegador modifique datos
    if x_maceta != "1":
        raise HTTPException(403, "Falta la cabecera X-Maceta")


def crear_app(base, consultar=True):
    ing = Ingesta(base)

    @asynccontextmanager
    async def vida(_):
        if consultar:
            ing.sincronizar()
        yield
        ing.parar.set()

    # Sin /docs: cargaría archivos de internet
    app = FastAPI(title="Maceta central", lifespan=vida, docs_url=None, redoc_url=None, openapi_url=None)

    def resumen(m):
        v = ing.vigilantes.get(m["id"])
        return {**m, "origen": base.tipo, "conectada": bool(v and v.conectada),
                "error": v.error if v else None, "vivo": v.vivo if v and v.conectada else None}

    def buscar(mid):
        for m in base.macetas():
            if m["id"] == mid:
                return m
        raise HTTPException(404, "No existe esa maceta")

    @app.get("/api/v1/salud")
    def salud():
        return {"ok": True, "tipo": base.tipo, "hora": int(time.time())}

    @app.get("/api/v1/macetas")
    def listar():
        return [resumen(m) for m in base.macetas()]

    @app.post("/api/v1/macetas", status_code=201, dependencies=[Depends(permitido)])
    def crear(n: NuevaMaceta):
        try:
            mid = base.crear_maceta(n.nombre, n.url, n.especie)
        except Conflicto as e:
            raise HTTPException(409, str(e))
        if consultar:
            ing.sincronizar()
        return {"id": mid}

    @app.get("/api/v1/macetas/{mid}")
    def una(mid: str):
        return resumen(buscar(mid))

    @app.patch("/api/v1/macetas/{mid}/direccion", dependencies=[Depends(permitido)])
    def direccion(mid: str, d: Direccion):
        buscar(mid)
        try:
            base.cambiar_url(mid, d.url)
        except Conflicto as e:
            raise HTTPException(409, str(e))
        if mid in ing.vigilantes:
            ing.vigilantes[mid].cambiar_url(d.url)
        return {"ok": True}

    @app.get("/api/v1/macetas/{mid}/lecturas")
    def lecturas(mid: str, desde: int = Query(0, ge=0, le=2**40), hasta: int | None = Query(None, ge=0, le=2**40),
                 limite: int = Query(5000, ge=1, le=20000)):
        buscar(mid)
        return base.lecturas(mid, desde, hasta, limite)

    @app.get("/api/v1/macetas/{mid}/diario")
    def diario(mid: str):
        buscar(mid)
        return base.diario(mid)

    return app
