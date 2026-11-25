import urllib.request

import pytest
from fastapi.testclient import TestClient

from maceta_central import virtuales as vi
from maceta_central.acceso import Acceso
from maceta_central.app import crear_app
from maceta_central.base import Base

H = {"X-Maceta": "1"}


@pytest.fixture(autouse=True)
def puertos(monkeypatch):
    monkeypatch.setattr(vi, "PUERTOS", range(8390, 8393))   # lejos de los que esté usando el usuario


def responde(url):
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url + "/api/estado", timeout=3) as r:
            return b'"simulada": true' in r.read()
    except OSError:
        return False


def test_crear_sin_direccion_y_borrar(tmp_path):
    b, s = Base(tmp_path / "real.db"), Base(tmp_path / "simulado.db", "simulado")
    with TestClient(crear_app(b, s, consultar=False)) as c:
        def alta(n, **k):
            return c.post("/api/v1/macetas", headers=H, json={"nombre": n, **k})
        assert alta("R").status_code == 422 and alta("R", origen="real").status_code == 422
        assert alta("X", origen="simulado", escenario="otro").status_code == 422
        ids = [alta(f"S{i}", origen="simulado", escenario=e).json()["id"] for i, e in enumerate(("sana", "sed", "sana"))]
        urls = [m["url"] for m in s.macetas()]
        assert len(set(urls)) == 3 and all(responde(u) for u in urls)
        assert alta("S4", origen="simulado").status_code == 409 and b.macetas() == []
        u = next(m["url"] for m in s.macetas() if m["id"] == ids[0])
        assert c.delete(f"/api/v1/macetas/{ids[0]}", headers=H).status_code == 200
        assert not responde(u) and alta("S5", origen="simulado").status_code == 201 and responde(u)
    assert not any(responde(x) for x in urls)      # se apagan con el servidor


def test_al_reabrir_se_encienden_y_respetan_las_ajenas(tmp_path):
    s = Base(tmp_path / "simulado.db", "simulado")
    v = vi.Virtuales(s)
    v.crear("A", "", "sed")
    s.crear_maceta("De antes", "http://127.0.0.1:8391")     # registrada a mano, sin simulador
    s.crear_maceta("De la demo", "http://127.0.0.1:8101")
    v.detener()
    v2 = vi.Virtuales(Base(tmp_path / "simulado.db", "simulado"))
    v2.iniciar()
    assert set(v2.activas) == {8390, 8391} and responde("http://127.0.0.1:8390")
    otra = vi.Virtuales(Base(tmp_path / "simulado.db", "simulado"))
    otra.iniciar()
    assert otra.activas == {}                               # ya hay un simulador: no se duplica
    v2.detener()


def test_el_celular_no_crea_simuladas(tmp_path):
    b, s = Base(tmp_path / "real.db"), Base(tmp_path / "simulado.db", "simulado")
    app = crear_app(b, s, consultar=False, acceso=Acceso(8000, con_codigo=False))
    c = TestClient(app, base_url="http://10.0.0.2:8000", client=("10.0.0.9", 5))
    for k in ({"origen": "simulado"}, {}):
        assert c.post("/api/v1/macetas", headers=H, json={"nombre": "X", **k}).status_code == 403
    assert s.macetas() == []
