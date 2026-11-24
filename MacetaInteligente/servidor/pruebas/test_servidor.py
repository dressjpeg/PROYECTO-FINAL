import re
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from maceta_central import adaptador_http as api
from maceta_central.app import crear_app
from maceta_central.base import Base, Conflicto, calidad
from maceta_central.ingesta import Ingesta, Vigilante
from simulador.maceta_virtual import CAMPOS, CAMPOS_DIA, Simulacion, servidor

FW = Path(__file__).resolve().parents[2] / "maceta_inteligente" / "Dashboard.ino"
T0 = 1_800_000_000


@pytest.fixture
def base(tmp_path):
    return Base(tmp_path / "real.db")


@pytest.fixture
def sim(tmp_path):
    return Base(tmp_path / "sim.db", "simulado")


@pytest.fixture
def virtual():
    s = servidor(0, "sed")
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_address[1]}"
    s.shutdown()
    s.server_close()


def alta(b, url="http://10.0.0.5", nombre="M"):
    mid = b.crear_maceta(nombre, url)
    return next(m for m in b.macetas() if m["id"] == mid)


def hist(*filas, ahora=T0, uptime=1000, arranque=3):
    return {"hora_real": ahora > 0, "ahora": ahora, "uptime_s": uptime, "arranque": arranque, "datos": list(filas)}


def fila(t, fuente, hr=3000, arranque=3):
    return [t, fuente, 44, 60, 90, 4, hr, 1000, arranque]


def guardar(b, m, r, t=T0):
    return b.guardar_historial(m["id"], m["dispositivo_id"], r, t)


def todas(b):
    with b.con() as c:
        return [dict(f) for f in c.execute("SELECT * FROM lecturas ORDER BY id")]


# ----- Sin duplicados y horas -----
def test_real_sin_duplicados(base):
    m = alta(base)
    r = hist(fila(T0 - 600, 1), fila(T0 - 300, 1))
    assert guardar(base, m, r) == 2
    assert guardar(base, m, r) == 0


def test_corregida_se_mueve_un_segundo(base):
    m = alta(base)
    assert guardar(base, m, hist(fila(T0 - 600, 2))) == 1
    assert guardar(base, m, hist(fila(T0 - 601, 2), ahora=T0 + 300, uptime=1300)) == 0
    assert len(todas(base)) == 1


def test_sin_hora_usa_la_del_servidor_y_luego_no_se_duplica(base):
    m = alta(base)
    assert guardar(base, m, hist(fila(400, 0), ahora=0)) == 1
    assert todas(base)[0]["t"] == T0 - 600 and todas(base)[0]["fuente_hora"] == "servidor"
    assert guardar(base, m, hist(fila(T0 - 600, 2))) == 0
    # Tras reiniciar, la misma lectura vuelve como "sin hora" de otro arranque
    assert guardar(base, m, hist(fila(400, 0), uptime=50, arranque=4)) == 0


def test_otro_arranque_sin_hora_no_inventa_fecha(base):
    m = alta(base)
    assert guardar(base, m, hist(fila(400, 0, arranque=2))) == 1
    assert todas(base)[0]["t"] is None and base.lecturas(m["id"]) == []


def test_lecturas_iguales_cada_5_min_no_se_confunden(base):
    m = alta(base)
    assert guardar(base, m, hist(fila(100, 0), fila(400, 0), fila(700, 0), ahora=0)) == 3


def test_dos_macetas_no_se_mezclan(base):
    a, b = alta(base), alta(base, "http://10.0.0.6")
    r = hist(fila(T0 - 300, 1))
    assert guardar(base, a, r) == 1 and guardar(base, b, r) == 1
    assert len(base.lecturas(a["id"])) == len(base.lecturas(b["id"])) == 1


def test_calibracion_solo_al_cambiar(base):
    d = alta(base)["dispositivo_id"]
    for c in ({"x": 1}, {"x": 1}, {"x": 2}):
        base.guardar_config(d, c, T0)
    with base.con() as c:
        assert c.execute("SELECT COUNT(*) FROM calibraciones").fetchone()[0] == 2


def test_calidad():
    assert calidad(3000, 1000) == "ok"
    assert calidad(4095, 93) == "hum_saturada,luz_fuera_de_rango"


def test_base_no_cambia_de_tipo(base):
    with pytest.raises(Conflicto):
        Base(base.ruta, "simulado")


# ----- Ingesta contra la maceta virtual -----
def test_ciclo_completo_y_repetido(sim, virtual):
    v = Vigilante(sim, alta(sim, virtual))
    assert v.ciclo() and v.conectada
    n = len(todas(sim))
    assert n == 2016 and len(sim.diario(v.mid)) == 6
    v.t_intento_hist = v.t_diario = None
    assert v.ciclo()
    assert len(todas(sim)) - n <= 1   # como mucho la lectura de este momento


def test_recupera_tras_corte(sim, virtual):
    reloj = [time.time()]
    v = Vigilante(sim, alta(sim, virtual), lambda: reloj[0])
    assert v.ciclo()
    with sim.con() as c:   # corte de 2 h: faltan las últimas 24 lecturas
        c.execute("DELETE FROM lecturas WHERE id IN (SELECT id FROM lecturas ORDER BY t DESC LIMIT 24)")
    reloj[0] += 7200
    assert not v.conectada and v.rango() == "24h"
    assert v.ciclo()
    assert len(todas(sim)) in (2016, 2017)


def test_reinicio_del_servidor_pide_7_dias(sim, virtual):
    m = alta(sim, virtual)
    assert Vigilante(sim, m).ciclo()
    v = Vigilante(sim, m)
    assert v.rango() == "7d" and v.ciclo()
    assert len(todas(sim)) in (2016, 2017)


def test_base_real_rechaza_simulada(base, virtual):
    v = Vigilante(base, alta(base, virtual))
    assert not v.ciclo() and "real" in v.error
    assert todas(base) == []


def test_apagada_no_afecta(base):
    v = Vigilante(base, alta(base, "http://127.0.0.1:9"))
    assert not v.ciclo() and not v.conectada and v.error


def test_cambio_de_direccion_descarta_respuesta_vieja(sim, virtual, monkeypatch):
    v = Vigilante(sim, alta(sim, virtual))
    orig = api.historial

    def lento(url, rango):
        r = orig(url, rango)
        v.cambiar_url("http://10.0.0.9")
        return r
    monkeypatch.setattr(api, "historial", lento)
    assert not v.ciclo()
    assert todas(sim) == [] and not v.conectada


def test_historial_malformado(monkeypatch):
    for filas in ([[1, 2]], [[T0, 1, 44, 60, 90, 9, 3000, 1000, 3]], [[T0, 1, "x", 60, 90, 4, 3000, 1000, 3]], None):
        monkeypatch.setattr(api, "_pedir", lambda *a, f=filas: {"ahora": T0, "uptime_s": 1, "arranque": 1, "datos": f})
        with pytest.raises(api.RespuestaInvalida):
            api.historial("http://x", "1h")


def test_veinte_virtuales_a_la_vez(sim):
    ss = [servidor(0, "sana") for _ in range(20)]
    ing = Ingesta(sim)
    try:
        for s in ss:
            threading.Thread(target=s.serve_forever, daemon=True).start()
            alta(sim, f"http://127.0.0.1:{s.server_address[1]}")
        ing.sincronizar()
        fin = time.time() + 60
        while time.time() < fin and not all(v.t_hist and v.conectada for v in ing.vigilantes.values()):
            time.sleep(.2)
        assert len(ing.vigilantes) == 20 and all(v.conectada for v in ing.vigilantes.values())
        assert all(2016 <= m["lecturas"] <= 2017 for m in sim.macetas())
    finally:
        ing.parar.set()
        for s in ss:
            s.shutdown()
            s.server_close()


# ----- API -----
def test_api(base):
    c, h = TestClient(crear_app(base, consultar=False)), {"X-Maceta": "1"}
    n = {"nombre": "Albahaca", "url": "maceta.local"}
    assert c.post("/api/v1/macetas", json=n).status_code == 403
    mid = c.post("/api/v1/macetas", json=n, headers=h).json()["id"]
    assert c.post("/api/v1/macetas", json=n, headers=h).status_code == 409
    assert c.post("/api/v1/macetas", json={**n, "nombre": "  "}, headers=h).status_code == 422
    assert c.post("/api/v1/macetas", json={**n, "url": "http://example.com"}, headers=h).status_code == 422
    assert c.patch(f"/api/v1/macetas/{mid}/direccion", json={"url": "192.168.43.7"}, headers=h).status_code == 200
    m = c.get("/api/v1/macetas").json()[0]
    assert m["url"] == "http://192.168.43.7" and m["conectada"] is False and m["origen"] == "real"
    assert c.get(f"/api/v1/macetas/{mid}/lecturas").json() == []
    assert c.get("/api/v1/macetas/x/lecturas").status_code == 404


def test_real_y_simulada_en_un_servidor(base, sim):
    c, h = TestClient(crear_app(base, sim, consultar=False)), {"X-Maceta": "1"}
    r = c.post("/api/v1/macetas", json={"nombre": "R", "url": "10.0.0.5"}, headers=h).json()["id"]
    s = c.post("/api/v1/macetas", json={"nombre": "S", "url": "10.0.0.6", "origen": "simulado"}, headers=h).json()["id"]
    assert {m["id"]: m["origen"] for m in c.get("/api/v1/macetas").json()} == {r: "real", s: "simulado"}
    assert [m["nombre"] for m in base.macetas()] == ["R"] and [m["nombre"] for m in sim.macetas()] == ["S"]
    assert c.get(f"/api/v1/macetas/{s}").json()["config"] is None
    solo = TestClient(crear_app(base, consultar=False))
    assert solo.post("/api/v1/macetas", json={"nombre": "S", "url": "10.0.0.7", "origen": "simulado"}, headers=h).status_code == 400


def test_dashboard_sin_recursos_externos(base):
    c = TestClient(crear_app(base, consultar=False))
    for f in ("/", "/app.js", "/jardin.js", "/jardin.css", "/escala.js", "/escala.css", "/grafica.js", "/avatar.js", "/estilo.css", "/avatar.css"):
        r = c.get(f)
        assert r.status_code == 200
        assert not re.search(r"(src|href)=[\"']?(https?:)?//|@import|url\(\s*[\"']?http", r.text), f


@pytest.mark.parametrize("u", ["https://10.0.0.1", "http://8.8.8.8", "http://10.0.0.1/x", "http://a:b@10.0.0.1",
                               "file:///c:/x", "http://0.0.0.0", "http://10.0.0.1:99999", "", "http://[::1"])
def test_url_rechazada(u):
    with pytest.raises(ValueError):
        api.validar_url(u)


# ----- Capacidad -----
def test_capacidad(base, sim, tmp_path):
    c, h = TestClient(crear_app(base, sim, consultar=False)), {"X-Maceta": "1"}
    alta(base)
    for i in range(4):
        alta(sim, f"http://127.0.0.1:{9100 + i}")
    d = c.get("/api/v1/capacidad").json()
    assert d["capacidad"] is None and d["registradas"] == 1 and d["conectadas"] == 0   # sin dato de WiFi no se inventa
    cfg = {"red": "Hotspot", "limite_wifi": 6, "otros_equipos": 1, "anios": 3}
    assert c.put("/api/v1/capacidad", json=cfg).status_code == 403
    assert c.put("/api/v1/capacidad", json={**cfg, "limite_wifi": 0}, headers=h).status_code == 422
    assert c.put("/api/v1/capacidad", json=cfg, headers=h).status_code == 200
    d = c.get("/api/v1/capacidad").json()
    assert (d["capacidad"], d["disponible"], d["limitante"]) == (5, 4, "Red WiFi")
    (tmp_path / "carga.json").write_text('{"fecha":1,"niveles":[{"macetas":3,"ok":true},{"macetas":9,"ok":false}]}')
    d = c.get("/api/v1/capacidad").json()
    assert (d["capacidad"], d["limitante"]) == (3, "Servidor y base de datos")
    (tmp_path / "carga.json").write_text("roto")
    assert c.get("/api/v1/capacidad").json()["capacidad"] == 5
    for i in range(6):
        alta(base, f"http://10.0.1.{i + 1}")
    d = c.get("/api/v1/capacidad").json()
    assert d["excedida"] and d["disponible"] == 0


# ----- Línea base: el firmware sigue ofreciendo lo mismo -----
RUTAS = {("/", "GET"), ("/api/estado", "GET"), ("/api/config", "GET"), ("/api/historial", "GET"), ("/api/historial.csv", "GET"),
         ("/api/diario", "GET"), ("/api/diario.csv", "GET"), ("/api/crecimiento", "GET"), ("/api/crecimiento", "POST"),
         ("/api/crecimiento", "DELETE"), ("/api/crecimiento.csv", "GET"), ("/api/riego", "POST")}


def funcion(nombre):
    src = FW.read_text(encoding="utf-8")
    i = src.index(f"void {nombre}()")
    return src[i:src.index("\n}", i)]


def test_rutas_del_firmware():
    src = FW.read_text(encoding="utf-8")
    assert RUTAS <= set(re.findall(r'servidor\.on\("([^"]+)", HTTP_(\w+)', src))


def test_virtual_igual_que_firmware():
    s = Simulacion()

    def claves(f):
        return set(re.findall(r'\\"(\w+)\\":', funcion(f)))

    def de(d):
        r = set()
        for k, v in d.items():
            r.add(k)
            if isinstance(v, dict):
                r |= de(v)
        return r
    anidadas = {"clave", "texto", "desde_s", "inicio", "fin", "duracion_s"}
    assert de(s.estado()) - {"simulada", "luz_lx", "temp_c"} == claves("apiEstado") - anidadas
    assert de(s.config()) - {"simulada"} == claves("apiConfig")
    for f, campos in (("apiHistorial", CAMPOS), ("apiDiario", CAMPOS_DIA)):
        assert all(f'\\"{x}\\"' in funcion(f) for x in campos)
