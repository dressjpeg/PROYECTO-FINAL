import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from maceta_central import acceso as ac
from maceta_central import certificado
from maceta_central.app import crear_app
from maceta_central.base import Base

H = {"X-Maceta": "1"}


@pytest.fixture
def srv(tmp_path):
    b = Base(tmp_path / "real.db")
    a = ac.Acceso(8443)
    app = crear_app(b, consultar=False, acceso=a)

    def cliente(ip="10.0.0.9", host="10.0.0.2:8443"):
        return TestClient(app, base_url=f"https://{host}", client=(ip, 5000), follow_redirects=False)
    cliente.base = b
    return a, cliente, b.crear_maceta("A", "http://10.0.0.1")


def entra(c, a, codigo=None):
    return c.post("/entrar", data={"codigo": codigo or a.nuevo_codigo()})


def test_sin_codigo_no_se_ve_nada(srv):
    a, cliente, m = srv
    c = cliente()
    for u in ("/api/v1/macetas", "/api/v1/salud", "/api/v1/acceso", "/api/v1/capacidad", f"/api/v1/macetas/{m}/fotos"):
        assert c.get(u, headers=H).status_code == 401
    for u in ("/", "/app.js", "/cualquiera", "/docs", "/openapi.json"):
        r = c.get(u)
        assert r.status_code == 303 and r.headers["location"] == "/entrar"
    assert c.get("/entrar").status_code == 200
    assert c.post(f"/api/v1/macetas/{m}/fotos", content=b"x", headers=H).status_code == 401
    c.cookies.set(ac.COOKIE, "inventada")
    assert c.get("/api/v1/macetas", headers=H).status_code == 401
    assert c.post("/entrar", data={"codigo": ""}).status_code == 401     # sin código creado no entra nadie


def test_con_codigo_usa_fotos_pero_no_administra(srv):
    a, cliente, m = srv
    c = cliente()
    r = entra(c, a)
    g = r.headers["set-cookie"].lower()
    assert r.status_code == 303 and all(x in g for x in ("httponly", "secure", "samesite=strict"))
    assert c.get("/").status_code == 200
    b = io.BytesIO()
    Image.new("RGB", (50, 50), "green").save(b, "JPEG")
    u = f"/api/v1/macetas/{m}/fotos"
    assert c.post(u, content=b.getvalue()).status_code == 403                # sigue exigiendo X-Maceta
    fid = c.post(u, content=b.getvalue(), headers=H).json()["id"]
    assert c.get(f"{u}/{fid}/mini.jpg").status_code == 200
    assert c.delete(f"{u}/{fid}", headers=H).status_code == 200
    assert c.post(f"{u}/{fid}/restaurar", headers=H).status_code == 200
    assert c.delete(f"/api/v1/macetas/{m}", headers=H, params={"nombre": "A"}).status_code == 403
    assert c.post("/api/v1/macetas", json={"nombre": "B", "url": "http://10.0.0.3"}).status_code == 403
    assert c.patch(f"/api/v1/macetas/{m}/direccion", headers=H, json={"url": "http://10.0.0.3"}).status_code == 403
    assert c.put("/api/v1/capacidad", headers=H, json={"red": "x"}).status_code == 403
    for u in ("codigo", "cerrar"):
        assert c.post(f"/api/v1/acceso/{u}", headers=H).status_code == 403


def test_codigo_de_un_uso_vence_y_no_se_guarda(srv):
    a, cliente, _ = srv
    cod = a.nuevo_codigo()
    assert cod not in repr(vars(a)) and cod.encode() not in b"".join(x for x in a.clave if isinstance(x, bytes))
    assert entra(cliente(), a, cod).status_code == 303
    assert entra(cliente("10.0.0.8"), a, cod).status_code == 401
    cod = a.nuevo_codigo()
    a.clave[2] = 1
    assert entra(cliente("10.0.0.7"), a, cod).status_code == 401
    viejo, nuevo = a.nuevo_codigo(), a.nuevo_codigo()
    assert entra(cliente("10.0.0.6"), a, viejo).status_code == 401
    assert entra(cliente("10.0.0.6"), a, nuevo[:4] + " " + nuevo[4:]).status_code == 303


def test_limites_de_intentos(srv):
    a, cliente, _ = srv
    c, cod = cliente(), a.nuevo_codigo()
    for _ in range(ac.INTENTOS):
        assert entra(c, a, "x").status_code == 401
    assert entra(c, a, cod).status_code == 429
    a.fallos["10.0.0.9"] = (ac.INTENTOS, 1)      # pasó el bloqueo
    for i in range(ac.FALLOS_CODIGO - ac.INTENTOS):
        assert entra(cliente(f"10.0.1.{i}"), a, "x").status_code == 401
    assert a.vigente() is None and entra(c, a, cod).status_code == 401       # el código se anuló
    assert c.post("/entrar", content=b"x" * 500).status_code == 413


def test_el_celular_no_recibe_datos_sensibles(srv):
    a, cliente, m = srv
    b = cliente.base
    d = b.macetas()[0]["dispositivo_id"]
    b.guardar_historial(m, d, {"ahora": 1795000000, "uptime_s": 9, "arranque": 1, "datos": [[1794999800, 1, 44, 60, 90, 4, 3000, 1000, 1]]}, 1795000000)
    c = cliente()
    entra(c, a)
    todo = ""
    for u in ("macetas", f"macetas/{m}", f"macetas/{m}/lecturas", "capacidad", "acceso", "salud"):
        assert c.get(f"/api/v1/{u}").status_code == 403                      # abierta a mano
        r = c.get(f"/api/v1/{u}", headers=H)
        assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
        todo += r.text
    assert d not in todo and "10.0.0.1" not in todo
    for x in ("url", "dispositivo_id", "hum_raw", "luz_raw", "arranque", "calibracion", "wifi_rssi", "heap_libre", '"codigo"', "codigo_vigente", "huella", "GB libres"):
        assert x not in todo, x
    v = ac.maceta_publica({"id": "x", "vivo": {"ip": "1", "wifi_rssi": -5, "hum_pct": 4}, "config": {"calibracion": {}, "umbrales": {"sed": 3}}})
    assert json.loads(json.dumps(v)) == {"id": "x", "vivo": {"hum_pct": 4}, "config": {"umbrales": {"sed": 3}}}


def test_cabeceras_de_seguridad(srv):
    a, cliente, _ = srv
    for r in (cliente().get("/entrar"), cliente().get("/"), cliente("127.0.0.1", "127.0.0.1:8000").get("/")):
        assert r.headers["x-frame-options"] == "DENY" and "default-src 'self'" in r.headers["content-security-policy"]
        assert r.headers["x-content-type-options"] == "nosniff"


def test_sesiones_vencen_y_se_cierran(srv):
    a, cliente, _ = srv
    c, pc = cliente(), cliente("127.0.0.1", "127.0.0.1:8000")
    ver = lambda: c.get("/api/v1/macetas", headers=H).status_code
    entra(c, a)
    assert c.cookies[ac.COOKIE] not in repr(a.sesiones)                      # solo su hash
    t = c.cookies[ac.COOKIE]
    assert c.post("/salir", headers=H).status_code == 200
    c.cookies.set(ac.COOKIE, t)
    assert ver() == 401                                                      # la galleta copiada ya no sirve
    c.cookies.clear()
    entra(c, a)
    a.sesiones = {k: 1 for k in a.sesiones}
    assert ver() == 401
    entra(c, a)
    assert ver() == 200 and pc.get("/api/v1/acceso").json()["sesiones"] == 1
    assert pc.post("/api/v1/acceso/cerrar").status_code == 403
    assert pc.post("/api/v1/acceso/cerrar", headers=H).status_code == 200 and ver() == 401


def test_solo_el_pc_crea_codigos(srv):
    a, cliente, _ = srv
    pc = cliente("127.0.0.1", "127.0.0.1:8000")
    assert "codigo" not in {k for k in pc.get("/api/v1/acceso").json() if k != "codigo_vigente"}
    assert pc.post("/api/v1/acceso/codigo").status_code == 403               # otra web no puede pedirlo
    cod = pc.post("/api/v1/acceso/codigo", headers=H).json()["codigo"]
    assert cliente("127.0.0.1", "sitio-externo.example").post("/api/v1/acceso/codigo", headers=H).status_code == 401
    assert cliente("10.0.0.9", "127.0.0.1:8000").post("/api/v1/acceso/codigo", headers=H).status_code == 401
    assert entra(cliente(), a, cod).status_code == 303


def test_certificado(tmp_path):
    cert, clave, h = certificado.obtener(tmp_path / "t")
    assert cert.is_file() and "PRIVATE KEY" in clave.read_text() and len(h) == 95
    assert certificado.obtener(tmp_path / "t")[2] == h
    cert.write_text("roto")
    assert certificado.obtener(tmp_path / "t")[2] != h


def test_sin_red_todo_sigue_igual(tmp_path):
    c = TestClient(crear_app(Base(tmp_path / "real.db"), consultar=False))
    assert c.get("/api/v1/acceso").json() == {"red": False, "remoto": False}
    assert c.post("/api/v1/acceso/codigo", headers=H).status_code == 403
    assert c.get("/").status_code == 200 and c.get("/api/v1/macetas").json() == []


def test_red_abierta_sin_codigo(tmp_path):
    b = Base(tmp_path / "real.db")
    m = b.crear_maceta("A", "http://10.0.0.1")
    app = crear_app(b, consultar=False, acceso=ac.Acceso(8000, con_codigo=False))

    def cliente(ip="10.0.0.9", host="10.0.0.2:8000"):
        return TestClient(app, base_url=f"http://{host}", client=(ip, 5000), follow_redirects=False)
    c = cliente()
    assert c.get("/").status_code == 200 and c.get("/entrar").status_code == 303
    assert c.get("/api/v1/macetas").status_code == 403
    r = c.get("/api/v1/macetas", headers=H)
    assert r.json()[0]["nombre"] == "A" and "10.0.0.1" not in r.text and "dispositivo_id" not in r.text
    assert c.get("/api/v1/acceso", headers=H).json() == {"red": True, "remoto": True, "con_codigo": False}
    i = io.BytesIO()
    Image.new("RGB", (50, 50), "green").save(i, "JPEG")
    assert c.post(f"/api/v1/macetas/{m}/fotos", content=i.getvalue(), headers=H).status_code == 201
    assert c.delete(f"/api/v1/macetas/{m}", headers=H, params={"nombre": "A"}).status_code == 403
    assert c.post("/api/v1/macetas", headers=H, json={"nombre": "B", "url": "http://10.0.0.3"}).status_code == 201
    assert cliente(host="sitio-externo.example").get("/api/v1/macetas", headers=H).status_code == 403
    assert cliente("10.0.0.9", "127.0.0.1:8000").delete(f"/api/v1/macetas/{m}", headers=H, params={"nombre": "A"}).status_code == 403
    pc = cliente("127.0.0.1", "127.0.0.1:8000")
    assert pc.get("/api/v1/acceso").json()["con_codigo"] is False
    assert pc.post("/api/v1/acceso/codigo", headers=H).status_code == 403
    assert pc.get("/api/v1/macetas").json()[0]["url"] == "http://10.0.0.1"


def test_el_celular_no_vacia_la_papelera(srv, tmp_path):
    a, cliente, m = srv
    c = cliente()
    entra(c, a)
    u = f"/api/v1/macetas/{m}/papelera?esperadas=0"
    for otra in (f"/api/v1/macetas/{m}/papelera/x", "/api/v1/papelera?esperadas=0"):
        assert c.delete(otra, headers=H).status_code == 403
    assert c.delete(u, headers=H).status_code == 403
    abierta = crear_app(Base(tmp_path / "x.db"), consultar=False, acceso=ac.Acceso(8000, con_codigo=False))
    assert TestClient(abierta, base_url="http://10.0.0.2:8000", client=("10.0.0.9", 5)).delete(u, headers=H).status_code == 403
    assert cliente("127.0.0.1", "127.0.0.1:8000").delete(u, headers=H).status_code == 200


def test_el_pc_por_su_ip_de_red_es_local(tmp_path):
    app = crear_app(Base(tmp_path / "x.db"), consultar=False, acceso=ac.Acceso(8000, con_codigo=False))

    def remoto(ip, host):
        r = TestClient(app, base_url=f"http://{host}:8000", client=(ip, 5)).get("/api/v1/acceso", headers=H)
        return r.json().get("remoto", r.status_code)
    assert remoto("10.0.0.2", "10.0.0.2") is False
    assert remoto("10.0.0.9", "10.0.0.2") is True
    # Host falso: el destino real de la conexión no cambia
    c = TestClient(app, base_url="http://10.0.0.2:8000", client=("10.0.0.9", 5))
    assert c.get("/api/v1/acceso", headers={**H, "Host": "10.0.0.9"}).json()["remoto"] is True
    c = TestClient(app, base_url="http://10.0.0.2:8000", client=("10.0.0.2", 5))
    assert c.get("/api/v1/acceso", headers={**H, "Host": "sitio-externo.example"}).status_code == 403


def test_agregar_desde_el_celular(tmp_path, monkeypatch):
    b, s = Base(tmp_path / "real.db"), Base(tmp_path / "simulado.db", "simulado")
    app = crear_app(b, s, consultar=False, acceso=ac.Acceso(8000, con_codigo=False))
    monkeypatch.setattr(ac, "direccion_red", lambda: "10.0.0.2")
    c = TestClient(app, base_url="http://10.0.0.2:8000", client=("10.0.0.9", 5))

    def alta(url, quien=c, **k):
        return quien.post("/api/v1/macetas", headers=H, json={"nombre": "N", "url": url, **k}).status_code
    for u in ("127.0.0.1", "http://localhost", "10.0.0.2", "10.0.0.5:22", "http://127.0.0.9:8101"):
        assert alta(u) == 403, u
    assert alta("8.8.8.8") == 422 and alta("10.0.0.6", origen="simulado") == 403
    assert alta("10.0.0.6") == 201 and alta("maceta.local", origen="real") == 201 and alta("10.0.0.6") == 409
    assert len(b.macetas()) == 2 and s.macetas() == []
    monkeypatch.setattr(ac, "MAX_ALTA", 2)
    assert alta("10.0.0.7") == 403
    pc = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 5))
    assert alta("127.0.0.1:8101", pc, origen="simulado") == 201 and alta("10.0.0.7", pc) == 201
    mid = b.macetas()[0]["id"]
    assert c.delete(f"/api/v1/macetas/{mid}", headers=H, params={"nombre": "N"}).status_code == 403


def test_borrar_desde_el_celular_con_codigo_del_pc(tmp_path):
    b = Base(tmp_path / "real.db")
    a = ac.Acceso(8000, con_codigo=False)
    app = crear_app(b, consultar=False, acceso=a)
    x, y = b.crear_maceta("A", "http://10.0.0.1"), b.crear_maceta("B", "http://10.0.0.3")

    def cli(ip, host="10.0.0.2"):
        return TestClient(app, base_url=f"http://{host}:8000", client=(ip, 5))
    c, otro, pc = cli("10.0.0.9"), cli("10.0.0.8"), cli("127.0.0.1", "127.0.0.1")

    def pedir(m=x, quien=c):
        return quien.post(f"/api/v1/macetas/{m}/autorizacion", headers=H)

    def borrar(cod, m=x, quien=c):
        return quien.delete(f"/api/v1/macetas/{m}", headers={**H, "X-Autorizacion": cod}).status_code

    def codigo():
        k = pc.get("/api/v1/acceso/permiso").json()["permiso"]
        return k and k["codigo"]
    assert borrar("000000") == 403 and codigo() is None
    r = pedir()
    cod = codigo()
    assert r.status_code == 200 and cod not in r.text
    assert c.get("/api/v1/acceso/permiso", headers=H).status_code == 403          # el celular no puede leerlo
    assert c.delete("/api/v1/acceso/permiso", headers=H).status_code == 403
    assert pedir(quien=otro).status_code == 409
    assert borrar(cod, quien=otro) == 403 and borrar(cod, m=y) == 403             # atado al equipo y a la maceta
    mal = f"{(int(cod) + 1) % 10**6:06d}"
    assert borrar(mal) == 403 and borrar(cod[:3] + " " + cod[3:]) == 200          # admite espacios
    assert [m["id"] for m in b.macetas()] == [y] and list((tmp_path / "respaldos").glob("*.db"))
    pedir(y)
    cod = codigo()
    assert [borrar(f"{(int(cod) + i) % 10**6:06d}", m=y) for i in (1, 2, 3)] == [403] * 3
    assert codigo() is None and borrar(cod, m=y) == 403                           # 3 errores lo anulan
    pedir(y)
    cod = codigo()
    a.permiso["vence"] = 1
    assert borrar(cod, m=y) == 403                                                # vencido
    pedir(y)
    cod = codigo()
    assert pc.delete("/api/v1/acceso/permiso").status_code == 403
    assert pc.delete("/api/v1/acceso/permiso", headers=H).status_code == 200
    assert borrar(cod, m=y) == 403 and pedir(y).status_code == 429                # rechazado: debe esperar
    assert len(b.macetas()) == 1 and borrar("", m=y, quien=pc) == 200             # el PC sigue sin código
