import io
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from maceta_central import fotos
from maceta_central.app import crear_app
from maceta_central.base import Base

H = {"X-Maceta": "1"}


def jpg(color="green", tam=(2000, 1000), exif=None, formato="JPEG", modo="RGB"):
    b = io.BytesIO()
    kw = {"exif": exif} if exif else {}
    Image.new(modo, tam, color).save(b, formato, **kw)
    return b.getvalue()


def con_exif(fecha="2026:11:20 08:30:00", giro=None):
    e = Image.Exif()
    e[0x8769] = {0x9003: fecha}
    e[0x8825] = {1: "N", 2: (6.0, 15.0, 0.0)}
    if giro:
        e[0x0112] = giro
    return e


@pytest.fixture
def srv(tmp_path):
    b, s = Base(tmp_path / "real.db"), Base(tmp_path / "simulado.db", "simulado")
    c = TestClient(crear_app(b, s, consultar=False))
    return c, b, b.crear_maceta("A", "http://10.0.0.1"), b.crear_maceta("B", "http://10.0.0.2"), s.crear_maceta("S", "http://10.0.0.3")


def sube(c, m, datos, **q):
    return c.post(f"/api/v1/macetas/{m}/fotos", content=datos, headers=H, params=q)


def lista(c, m, **q):
    return c.get(f"/api/v1/macetas/{m}/fotos", params=q).json()


def test_sube_redimensiona_y_separa(srv):
    c, b, a, otra, s = srv
    assert c.post(f"/api/v1/macetas/{a}/fotos", content=jpg()).status_code == 403
    r = sube(c, a, jpg(), nota=" hoja nueva ", altura=12.5, hojas=4)
    assert r.status_code == 201
    f, = lista(c, a)
    assert (f["ancho"], f["alto"], f["nota"], f["altura_cm"], f["hojas"]) == (1600, 800, "hoja nueva", 12.5, 4)
    assert f["fuente_fecha"] == "subida" and abs(f["capturada_en"] - time.time()) < 10
    assert lista(c, otra) == [] and lista(c, s) == []
    for t, lado in (("grande", 1600), ("mini", 320)):
        g = c.get(f"/api/v1/macetas/{a}/fotos/{f['id']}/{t}.jpg")
        assert g.status_code == 200 and Image.open(io.BytesIO(g.content)).width == lado
    assert c.get(f"/api/v1/macetas/{otra}/fotos/{f['id']}/grande.jpg").status_code == 404   # no se ve desde otra maceta
    assert c.get(f"/api/v1/macetas/{a}/fotos/{f['id']}/otro.jpg").status_code == 404


def test_fecha_exif_sin_gps_y_girada(srv):
    c, b, a, *_ = srv
    datos = jpg(exif=con_exif(giro=6))
    assert Image.open(io.BytesIO(datos)).getexif().get_ifd(0x8825)   # la original sí trae GPS
    sube(c, a, datos)
    f, = lista(c, a)
    assert f["fuente_fecha"] == "exif" and time.strftime("%Y-%m-%d %H:%M", time.gmtime(f["capturada_en"])) == "2026-11-20 13:30"
    assert (f["ancho"], f["alto"]) == (800, 1600)
    img = Image.open(io.BytesIO(c.get(f"/api/v1/macetas/{a}/fotos/{f['id']}/grande.jpg").content))
    assert not img.getexif() and not img.getexif().get_ifd(0x8825)


def test_fuentes_de_fecha(srv):
    c, b, a, *_ = srv
    sube(c, a, jpg("red"), cuando=1795000000)
    sube(c, a, jpg("blue"), camara=True)
    sube(c, a, jpg("white", exif=con_exif("2090:01:01 00:00:00")))   # EXIF en el futuro: no se usa
    sube(c, a, jpg("black", exif=con_exif("basura")))
    assert sorted(f["fuente_fecha"] for f in lista(c, a)) == ["camara", "subida", "subida", "usuario"]
    assert sube(c, a, jpg("pink"), cuando=int(time.time()) + 90000).status_code == 422
    t = [f["capturada_en"] for f in lista(c, a)]
    assert t == sorted(t) and len(lista(c, a, hasta=1795000000)) == 1


def test_formatos_y_errores(srv):
    c, b, a, *_ = srv
    assert sube(c, a, jpg((0, 0, 0, 0), formato="PNG", modo="RGBA")).status_code == 201
    assert sube(c, a, jpg("gray", formato="WEBP")).status_code == 201
    assert sube(c, a, jpg(formato="GIF", modo="P", color=1)).status_code == 415
    assert sube(c, a, b"<script>alert(1)</script>").status_code == 415
    assert sube(c, a, jpg()[:500]).status_code == 415
    assert sube(c, a, b"").status_code == 422
    assert sube(c, a, b"x" * (fotos.MAX_BYTES + 1)).status_code == 413
    assert sube(c, "no-existe", jpg()).status_code == 404
    assert sube(c, a, jpg("olive"), altura=999).status_code == 422
    assert sube(c, a, jpg("navy")).status_code == 201 and sube(c, a, jpg("navy")).status_code == 409
    n = len(lista(c, a))
    assert n == 3 and len(list(fotos.carpeta(b).rglob("*.jpg"))) == 2 * n   # sin archivos huérfanos


def test_demasiados_pixeles(srv, monkeypatch):
    c, b, a, *_ = srv
    monkeypatch.setattr(fotos, "MAX_PIXELES", 1000)
    assert sube(c, a, jpg()).status_code == 413


def test_papelera(srv):
    c, b, a, *_ = srv
    fid = sube(c, a, jpg()).json()["id"]
    u = f"/api/v1/macetas/{a}/fotos/{fid}"
    assert c.delete(u).status_code == 403
    assert c.delete(u, headers=H).status_code == 200 and c.delete(u, headers=H).status_code == 404
    assert lista(c, a) == [] and len(lista(c, a, papelera=True)) == 1
    assert c.post(u + "/restaurar", headers=H).status_code == 200 and len(lista(c, a)) == 1
    c.delete(u, headers=H)
    assert sube(c, a, jpg()).status_code == 201
    assert c.post(u + "/restaurar", headers=H).status_code == 409   # ya hay una igual


def test_condiciones_cercanas(srv):
    c, b, a, *_ = srv
    d = next(m for m in b.macetas() if m["id"] == a)["dispositivo_id"]
    t = 1795000000
    b.guardar_historial(a, d, {"ahora": t, "uptime_s": 9, "arranque": 1, "datos": [[t - 200, 1, 44, 60, 90, 4, 3000, 1000, 1]]}, t)
    sube(c, a, jpg("red"), cuando=t)
    sube(c, a, jpg("blue"), cuando=t + 5000)
    x, y = lista(c, a)
    assert x["condiciones"]["hum_pct"] == 44 and y["condiciones"] is None


def test_borrar_maceta_conserva_las_imagenes(srv):
    c, b, a, otra, _ = srv
    sube(c, a, jpg())
    sube(c, otra, jpg())
    assert c.delete(f"/api/v1/macetas/{a}", headers=H).status_code == 409      # con fotos también pide el nombre
    assert c.delete(f"/api/v1/macetas/{a}", headers=H, params={"nombre": "A"}).status_code == 200
    assert len(lista(c, otra)) == 1 and c.get(f"/api/v1/macetas/{a}/fotos").status_code == 404
    assert len(list((b.ruta.parent / "respaldos" / f"fotos-{a}").rglob("*.jpg"))) == 2


def test_muchas_fotos(srv):
    c, b, a, *_ = srv
    with b.con() as k:
        k.executemany("INSERT INTO fotos VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)",
                      [(f"f{i}", a, "x", 1, 1795000000 + i, "exif", "", None, None, 1, 1, 1, str(i)) for i in range(500)])
    t = time.monotonic()
    assert len(lista(c, a)) == 500 and time.monotonic() - t < 2
