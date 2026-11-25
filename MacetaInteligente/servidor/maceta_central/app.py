"""API del servidor central y dashboard. Atiende una base real y, si se pide, otra simulada."""
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import acceso as acc
from . import capacidad as cap
from . import fotos
from .adaptador_http import validar_url
from .base import Conflicto, calidad
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
    origen: Literal["real", "simulado"] | None = None   # None = la base principal

    @field_validator("nombre", "especie", mode="before")
    @classmethod
    def _limpio(cls, v):
        return v.strip() if isinstance(v, str) else v


class ConfigCapacidad(BaseModel):
    red: str = Field(min_length=1, max_length=60)
    limite_wifi: int | None = Field(None, ge=1, le=1000)
    otros_equipos: int = Field(1, ge=0, le=1000)
    anios: int = Field(3, ge=1, le=20)


def permitido(x_maceta: str = Header("")):
    # Impide que otra web abierta en el navegador modifique datos
    if x_maceta != "1":
        raise HTTPException(403, "Falta la cabecera X-Maceta")


def crear_app(*bases, consultar=True, acceso=None):
    ings = {b.tipo: Ingesta(b) for b in bases}

    @asynccontextmanager
    async def vida(_):
        if consultar:
            for i in ings.values():
                i.sincronizar()
        yield
        for i in ings.values():
            i.parar.set()

    # Sin /docs: cargaría archivos de internet
    app = FastAPI(title="Maceta central", lifespan=vida, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def sin_cache(pedido, seguir):
        r = await seguir(pedido)
        r.headers["Cache-Control"] = "no-cache"
        return r

    def resumen(base, m):
        v = ings[base.tipo].vigilantes.get(m["id"])
        vivo = v.vivo if v and v.conectada else None
        return {**m, "fotos": fotos.hay(base, m["id"]), "origen": base.tipo, "conectada": bool(vivo), "error": v.error if v else None, "vivo": vivo,
                "calidad": calidad(vivo["hum_raw"], vivo["luz_raw"]).split(",") if vivo else []}

    def buscar(mid):
        for b in bases:
            for m in b.macetas():
                if m["id"] == mid:
                    return b, m
        raise HTTPException(404, "No existe esa maceta")

    @app.get("/api/v1/salud")
    def salud():
        return {"ok": True, "tipos": list(ings), "hora": int(time.time())}

    @app.get("/api/v1/macetas")
    def listar(p: Request):
        L = [resumen(b, m) for b in bases for m in b.macetas()]
        return [acc.maceta_publica(m) for m in L] if acc.remoto(p) else L

    @app.post("/api/v1/macetas", status_code=201, dependencies=[Depends(permitido)])
    def crear(n: NuevaMaceta):
        tipo = n.origen or bases[0].tipo
        if tipo not in ings:
            raise HTTPException(400, f"Este servidor no admite macetas de tipo {tipo}")
        try:
            mid = ings[tipo].base.crear_maceta(n.nombre, n.url, n.especie)
        except Conflicto as e:
            raise HTTPException(409, str(e))
        if consultar:
            ings[tipo].sincronizar()
        return {"id": mid}

    @app.get("/api/v1/macetas/{mid}")
    def una(mid: str, p: Request):
        b, m = buscar(mid)
        d = {**resumen(b, m), "config": b.config(m["dispositivo_id"])}
        return acc.maceta_publica(d) if acc.remoto(p) else d

    @app.patch("/api/v1/macetas/{mid}/direccion", dependencies=[Depends(permitido)])
    def direccion(mid: str, d: Direccion):
        b, _ = buscar(mid)
        try:
            b.cambiar_url(mid, d.url)
        except Conflicto as e:
            raise HTTPException(409, str(e))
        v = ings[b.tipo].vigilantes.get(mid)
        if v:
            v.cambiar_url(d.url)
        return {"ok": True}

    @app.delete("/api/v1/macetas/{mid}", dependencies=[Depends(permitido)])
    def borrar(mid: str, nombre: str = ""):
        b, m = buscar(mid)
        # Con historial hay que escribir el nombre: evita borrar la maceta equivocada
        if (m["lecturas"] or fotos.hay(b, mid)) and nombre.strip() != m["nombre"]:
            raise HTTPException(409, "Escribe el nombre exacto de la maceta para borrarla")
        r = ings[b.tipo].borrar(mid)
        fotos.archivar(b, mid)
        return {"ok": True, "respaldo": r}

    @app.get("/api/v1/macetas/{mid}/lecturas")
    def lecturas(mid: str, p: Request, desde: int = Query(0, ge=0, le=2**40), hasta: int | None = Query(None, ge=0, le=2**40),
                 limite: int = Query(5000, ge=1, le=20000)):
        L = buscar(mid)[0].lecturas(mid, desde, hasta, limite)
        return [acc.lectura_publica(x) for x in L] if acc.remoto(p) else L

    @app.get("/api/v1/macetas/{mid}/diario")
    def diario(mid: str):
        return buscar(mid)[0].diario(mid)

    @app.get("/api/v1/capacidad")
    def capacidad(p: Request):
        reales = [resumen(b, m) for b in bases if b.tipo == "real" for m in b.macetas()]
        vs = ings["real"].vigilantes.values() if "real" in ings else []
        d = cap.calcular(bases, sum(m["conectada"] for m in reales), len(reales),
                         [x for v in list(vs) for x in list(v.latencias)])
        return acc.capacidad_publica(d) if acc.remoto(p) else d

    @app.put("/api/v1/capacidad", dependencies=[Depends(permitido)])
    def config_capacidad(c: ConfigCapacidad):
        cap.guardar_config(bases[0], c.model_dump())
        return {"ok": True}

    fotos.registrar(app, bases, buscar, permitido)
    acc.registrar(app, acceso, permitido)
    app.mount("/", StaticFiles(directory=Path(__file__).parent / "web", html=True))
    return app
