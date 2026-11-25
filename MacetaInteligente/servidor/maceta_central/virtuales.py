"""Macetas simuladas que enciende el propio servidor, para que el formulario no pida dirección.
Usan los puertos 8105 a 8199 de este PC; las cuatro de simulador.demo siguen aparte (8101 a 8104)."""
import re
import socket
import threading

from fastapi import HTTPException

PUERTOS = range(8105, 8200)
ESQUEMA = "CREATE TABLE IF NOT EXISTS virtuales(maceta_id TEXT PRIMARY KEY REFERENCES macetas(id), escenario TEXT NOT NULL)"


def _puerto(url):
    m = re.fullmatch(r"http://127\.0\.0\.1:(\d+)", url)
    return int(m[1]) if m and int(m[1]) in PUERTOS else None


def _ocupado(puerto):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


class Virtuales:
    def __init__(self, base):
        self.base, self.activas, self.candado = base, {}, threading.Lock()
        with base.con() as c:
            c.execute(ESQUEMA)
        base.tablas_extra += ("virtuales",)   # para borrar_maceta

    def _encender(self, puerto, escenario):
        from simulador.maceta_virtual import servidor
        s = servidor(puerto, escenario)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        self.activas[puerto] = s

    def _apagar(self, puerto):
        s = self.activas.pop(puerto, None)
        if s:
            s.shutdown()
            s.server_close()

    def crear(self, nombre, especie, escenario):
        with self.candado:
            usados = {_puerto(m["url"]) for m in self.base.macetas()} | set(self.activas)
            for p in PUERTOS:
                if p not in usados and not _ocupado(p):
                    break
            else:
                raise HTTPException(409, "No quedan puertos libres para más macetas simuladas")
            self._encender(p, escenario)
            try:
                mid = self.base.crear_maceta(nombre, f"http://127.0.0.1:{p}", especie)
                with self.base.con() as c:
                    c.execute("INSERT INTO virtuales VALUES(?,?)", (mid, escenario))
            except Exception:
                self._apagar(p)
                raise
            return mid

    def iniciar(self):
        """Al abrir el servidor. Si ya hay un simulador en ese puerto, se usa ese."""
        with self.candado:
            with self.base.con() as c:
                esc = dict(tuple(f) for f in c.execute("SELECT maceta_id,escenario FROM virtuales"))
            for m in self.base.macetas():
                p = _puerto(m["url"])
                if p and p not in self.activas and not _ocupado(p):
                    self._encender(p, esc.get(m["id"], "sana"))

    def ajustar(self):
        """Apaga las que ya no corresponden a ninguna maceta (borradas o con otra dirección)."""
        with self.candado:
            for p in set(self.activas) - {_puerto(m["url"]) for m in self.base.macetas()}:
                self._apagar(p)

    def detener(self):
        with self.candado:
            for p in list(self.activas):
                self._apagar(p)
