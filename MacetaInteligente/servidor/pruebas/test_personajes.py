import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from maceta_central import personajes as pj
from maceta_central.acceso import Acceso
from maceta_central.app import crear_app
from maceta_central.base import Base

H = {"X-Maceta": "1"}


@pytest.fixture
def srv(tmp_path):
    b, s = Base(tmp_path / "real.db"), Base(tmp_path / "simulado.db", "simulado")
    app = crear_app(b, s, consultar=False, acceso=Acceso(8000, con_codigo=False))
    pc = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 5))
    cel = TestClient(app, base_url="http://10.0.0.2:8000", client=("10.0.0.9", 5))
    return pc, cel, b, s


def alta(c, url, **q):
    return c.post("/api/v1/macetas", headers=H, params=q, json={"nombre": "N", "url": url})


def ver(c):
    return c.get("/api/v1/personajes", headers=H).json()["asignados"]


def test_catalogo_completo():
    cat = pj.catalogo()
    assert cat[0]["id"] == pj.NORMAL and len({x["id"] for x in cat}) == len(cat)
    for x in cat:
        assert x["nombre"] and x["descripcion"]
        for k in (*pj.ESTADOS, "mini") if x.get("imagenes") else ():
            with Image.open(pj.CARPETA / x["id"] / f"{k}.webp") as i:
                assert i.size == (540, 500), (x["id"], k)
        if x.get("capas"):
            c = json.loads((pj.CARPETA / x["id"] / "capas.json").read_text(encoding="utf-8"))
            assert set(c["estados"]) == set(pj.ESTADOS)
            for y in [c["sol"], *(z for e in c["estados"].values() for z in e["cuerpo"] + e["efectos"])]:
                with Image.open(pj.CARPETA / x["id"] / y["f"]) as i:
                    assert i.mode == "RGBA", y["f"]


def test_elegir_al_crear_y_cambiar(srv):
    pc, cel, b, s = srv
    m = alta(pc, "10.0.0.1", personaje="bonsai").json()["id"]
    n = alta(pc, "10.0.0.2").json()["id"]
    assert ver(pc)[m] == "bonsai" and ver(pc).get(n, "maceta") == "maceta"
    assert alta(pc, "10.0.0.3", personaje="dragon").status_code == 422 and len(b.macetas()) == 2   # no queda a medias
    u = f"/api/v1/macetas/{n}/personaje"
    assert pc.put(u, json={"personaje": "bonsai"}).status_code == 403
    assert pc.put(u, headers=H, json={"personaje": "dragon"}).status_code == 422
    assert pc.put(u, headers=H, json={"personaje": "bonsai"}).status_code == 200 and ver(pc)[n] == "bonsai"
    assert pc.put(u, headers=H, json={"personaje": "maceta"}).status_code == 200 and ver(pc)[n] == "maceta"
    assert pc.put("/api/v1/macetas/x/personaje", headers=H, json={"personaje": "bonsai"}).status_code == 404


def test_celular_elige_al_crear_pero_no_cambia(srv):
    pc, cel, b, s = srv
    m = alta(cel, "10.0.0.5", personaje="bonsai").json()["id"]
    assert ver(cel)[m] == "bonsai"
    assert cel.put(f"/api/v1/macetas/{m}/personaje", headers=H, json={"personaje": "maceta"}).status_code == 403


def test_borrar_maceta_con_personaje(srv):
    pc, cel, b, s = srv
    m = alta(pc, "10.0.0.1", personaje="bonsai").json()["id"]
    assert pc.delete(f"/api/v1/macetas/{m}", headers=H).status_code == 200 and ver(pc) == {}


def test_base_anterior_sin_personajes(tmp_path):
    b = Base(tmp_path / "real.db")
    m = b.crear_maceta("A", "http://10.0.0.1")
    c = TestClient(crear_app(b, consultar=False))
    assert ver(c) == {} and c.get("/api/v1/macetas").json()[0]["id"] == m
    for x in ("personajes.js", "personajes/bonsai/feliz.webp"):
        assert c.get("/" + x).status_code == 200
