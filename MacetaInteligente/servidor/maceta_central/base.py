"""Base SQLite. Todo lo medido guarda de qué maceta, dispositivo y calibración viene.
Las fechas son epoch en segundos (UTC)."""
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS meta(clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS macetas(
  id TEXT PRIMARY KEY, nombre TEXT NOT NULL, especie TEXT NOT NULL DEFAULT '', creada_en INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS dispositivos(
  id TEXT PRIMARY KEY, url TEXT NOT NULL UNIQUE, creado_en INTEGER NOT NULL, ultimo_contacto INTEGER);
CREATE TABLE IF NOT EXISTS asignaciones(
  id INTEGER PRIMARY KEY, maceta_id TEXT NOT NULL REFERENCES macetas(id),
  dispositivo_id TEXT NOT NULL REFERENCES dispositivos(id), desde INTEGER NOT NULL, hasta INTEGER);
CREATE UNIQUE INDEX IF NOT EXISTS asig_maceta ON asignaciones(maceta_id) WHERE hasta IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS asig_disp ON asignaciones(dispositivo_id) WHERE hasta IS NULL;
CREATE TABLE IF NOT EXISTS calibraciones(
  id INTEGER PRIMARY KEY, dispositivo_id TEXT NOT NULL REFERENCES dispositivos(id),
  desde INTEGER NOT NULL, config TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lecturas(
  id INTEGER PRIMARY KEY, maceta_id TEXT NOT NULL REFERENCES macetas(id),
  dispositivo_id TEXT NOT NULL REFERENCES dispositivos(id),
  t INTEGER,                      -- NULL = no se pudo ubicar en el tiempo
  fuente_hora TEXT NOT NULL,      -- real | corregida | servidor | sin_hora
  arranque INTEGER NOT NULL, uptime INTEGER,
  hum_raw INTEGER NOT NULL, luz_raw INTEGER NOT NULL, hum_pct INTEGER NOT NULL, luz_pct INTEGER NOT NULL,
  indice INTEGER NOT NULL, estado INTEGER NOT NULL, calidad TEXT NOT NULL,
  calibracion_id INTEGER REFERENCES calibraciones(id),  -- la vigente al recibir la lectura
  recibida_en INTEGER NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS lect_real ON lecturas(dispositivo_id, arranque, t) WHERE fuente_hora = 'real';
CREATE INDEX IF NOT EXISTS lect_maceta ON lecturas(maceta_id, t);
CREATE INDEX IF NOT EXISTS lect_uptime ON lecturas(dispositivo_id, arranque, uptime);
CREATE TABLE IF NOT EXISTS diario(
  maceta_id TEXT NOT NULL REFERENCES macetas(id), dispositivo_id TEXT NOT NULL REFERENCES dispositivos(id),
  fecha TEXT NOT NULL, valores TEXT NOT NULL, PRIMARY KEY(dispositivo_id, fecha));
"""
TOLERANCIA_S = 60   # las lecturas van cada 300 s; la hora corregida puede moverse 1-2 s


class Conflicto(Exception):
    pass


def calidad(hum_raw, luz_raw):
    m = []
    if hum_raw >= 4090:
        m.append("hum_saturada")
    if hum_raw <= 0:
        m.append("hum_sin_senal")
    if luz_raw < 150 or luz_raw >= 4090:
        m.append("luz_fuera_de_rango")
    return ",".join(m) or "ok"


class Base:
    def __init__(self, ruta, tipo="real"):
        self.ruta, self.tipo = Path(ruta), tipo
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self.con() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript(ESQUEMA)
            c.execute("INSERT OR IGNORE INTO meta VALUES('tipo',?)", (tipo,))
            c.execute("INSERT OR IGNORE INTO meta VALUES('esquema','1')")
            guardado = c.execute("SELECT valor FROM meta WHERE clave='tipo'").fetchone()[0]
            if guardado != tipo:
                raise Conflicto(f"La base es de datos {guardado}, no {tipo}")

    @contextmanager
    def con(self):
        c = sqlite3.connect(self.ruta, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        try:
            with c:
                yield c
        finally:
            c.close()

    # ----- Macetas y dispositivos -----
    def crear_maceta(self, nombre, url, especie="", ident=None):
        ahora, mid, did = int(time.time()), str(uuid.uuid4()), ident or str(uuid.uuid4())
        try:
            with self.con() as c:
                c.execute("INSERT INTO macetas VALUES(?,?,?,?)", (mid, nombre, especie, ahora))
                c.execute("INSERT INTO dispositivos VALUES(?,?,?,NULL)", (did, url, ahora))
                c.execute("INSERT INTO asignaciones(maceta_id,dispositivo_id,desde) VALUES(?,?,?)", (mid, did, ahora))
        except sqlite3.IntegrityError as e:
            raise Conflicto("Ya hay una maceta con esa dirección") from e
        return mid

    def cambiar_url(self, mid, url):
        try:
            with self.con() as c:
                n = c.execute("UPDATE dispositivos SET url=? WHERE id=(SELECT dispositivo_id FROM asignaciones "
                              "WHERE maceta_id=? AND hasta IS NULL)", (url, mid)).rowcount
        except sqlite3.IntegrityError as e:
            raise Conflicto("Ya hay una maceta con esa dirección") from e
        return n > 0

    def macetas(self):
        with self.con() as c:
            return [dict(f) for f in c.execute(
                "SELECT m.id, m.nombre, m.especie, m.creada_en, d.id dispositivo_id, d.url, d.ultimo_contacto, "
                "(SELECT COUNT(*) FROM lecturas l WHERE l.maceta_id=m.id) lecturas FROM macetas m "
                "JOIN asignaciones a ON a.maceta_id=m.id AND a.hasta IS NULL "
                "JOIN dispositivos d ON d.id=a.dispositivo_id ORDER BY m.creada_en, m.nombre")]

    def contacto(self, did, t):
        with self.con() as c:
            c.execute("UPDATE dispositivos SET ultimo_contacto=? WHERE id=?", (int(t), did))

    # ----- Ingesta -----
    def guardar_config(self, did, config, t):
        txt = json.dumps(config, sort_keys=True)
        with self.con() as c:
            u = c.execute("SELECT config FROM calibraciones WHERE dispositivo_id=? ORDER BY id DESC LIMIT 1", (did,)).fetchone()
            if not u or u[0] != txt:
                c.execute("INSERT INTO calibraciones(dispositivo_id,desde,config) VALUES(?,?,?)", (did, int(t), txt))

    def guardar_historial(self, mid, did, r, recibido):
        """r = respuesta de /api/historial. Devuelve cuántas lecturas eran nuevas."""
        nuevas = 0
        with self.con() as c:
            c.execute("BEGIN IMMEDIATE")
            cal = c.execute("SELECT MAX(id) FROM calibraciones WHERE dispositivo_id=?", (did,)).fetchone()[0]
            for t0, fuente, hp, lp, ind, est, hr, lr, arr in r["datos"]:
                vals = (hr, lr, hp, lp, ind, est)
                if fuente == 1:
                    t, uptime, nombre = t0, None, "real"
                else:
                    uptime = t0 if fuente == 0 else r["uptime_s"] - (r["ahora"] - t0)
                    if fuente == 2:
                        t, nombre = t0, "corregida"
                    elif arr == r["arranque"]:
                        t, nombre = int(recibido - (r["uptime_s"] - t0)), "servidor"
                    else:
                        t, nombre = None, "sin_hora"
                    # La misma lectura puede volver con otra hora: se busca por tiempo encendida
                    v = c.execute(
                        "SELECT id, t FROM lecturas WHERE dispositivo_id=? AND arranque=? AND uptime BETWEEN ? AND ? "
                        "AND hum_raw=? AND luz_raw=? AND hum_pct=? AND luz_pct=? AND indice=? AND estado=? "
                        "ORDER BY ABS(uptime-?) LIMIT 1",
                        (did, arr, uptime - TOLERANCIA_S, uptime + TOLERANCIA_S, *vals, uptime)).fetchone()
                    if v:
                        if v["t"] is None and t is not None:
                            c.execute("UPDATE lecturas SET t=?, fuente_hora=? WHERE id=?", (t, nombre, v["id"]))
                        continue
                nuevas += c.execute(
                    "INSERT OR IGNORE INTO lecturas(maceta_id,dispositivo_id,t,fuente_hora,arranque,uptime,hum_raw,luz_raw,"
                    "hum_pct,luz_pct,indice,estado,calidad,calibracion_id,recibida_en) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (mid, did, t, nombre, arr, uptime, *vals, calidad(hr, lr), cal, int(recibido))).rowcount
        return nuevas

    def guardar_diario(self, mid, did, r):
        with self.con() as c:
            for d in r["dias"]:          # hoy_parcial no: aún cambia
                if d[0] != "sin_hora":
                    c.execute("INSERT INTO diario VALUES(?,?,?,?) ON CONFLICT(dispositivo_id,fecha) "
                              "DO UPDATE SET valores=excluded.valores",
                              (mid, did, d[0], json.dumps(dict(zip(r["campos"][1:], d[1:])))))

    # ----- Consultas -----
    def config(self, did):
        with self.con() as c:
            f = c.execute("SELECT config FROM calibraciones WHERE dispositivo_id=? ORDER BY id DESC LIMIT 1", (did,)).fetchone()
            return json.loads(f[0]) if f else None

    def lecturas(self, mid, desde=0, hasta=None, limite=5000):
        """Las más recientes del rango, en orden cronológico."""
        with self.con() as c:
            f = c.execute("SELECT t,fuente_hora,hum_raw,luz_raw,hum_pct,luz_pct,indice,estado,calidad,arranque FROM lecturas "
                          "WHERE maceta_id=? AND t>=? AND t<=? ORDER BY t DESC LIMIT ?",
                          (mid, desde, hasta if hasta is not None else 2**40, limite)).fetchall()
            return [dict(x) for x in reversed(f)]

    def diario(self, mid):
        with self.con() as c:
            return [{"fecha": f["fecha"], **json.loads(f["valores"])} for f in
                    c.execute("SELECT fecha,valores FROM diario WHERE maceta_id=? ORDER BY fecha", (mid,))]
