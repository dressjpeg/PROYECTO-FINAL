"""Consulta cada maceta en su propio hilo: si una falla, las demás siguen.
Nunca hay dos peticiones a la vez hacia la misma maceta."""
import logging
import threading
import time

from . import adaptador_http as api

log = logging.getLogger("maceta.ingesta")
T_ESTADO, T_HISTORIAL, T_DIARIO, T_CONECTADA = 10, 300, 3600, 30


class Vigilante:
    def __init__(self, base, maceta, reloj=time.time):
        self.base, self.reloj = base, reloj
        self.mid, self.did, self.url = maceta["id"], maceta["dispositivo_id"], maceta["url"]
        self.ultimo = maceta["ultimo_contacto"]
        self.vivo, self.error = None, None
        self.t_hist = self.t_diario = self.t_intento_hist = None
        self.generacion = 0   # cambia con la dirección: descarta respuestas de la anterior
        self.candado = threading.Lock()

    def cambiar_url(self, url):
        with self.candado:
            self.url, self.vivo, self.t_hist, self.t_diario, self.t_intento_hist = url, None, None, None, None
            self.ultimo = None
            self.generacion += 1

    def rango(self):
        if self.t_hist is None:
            return "7d"
        hueco = self.reloj() - self.t_hist
        return "1h" if 0 <= hueco < 3000 else "24h" if 0 <= hueco < 80000 else "7d"

    def ciclo(self):
        with self.candado:
            url, gen = self.url, self.generacion

        def si_vigente(f, *a):
            with self.candado:
                if gen != self.generacion:
                    raise api.SinConexion("Cambió la dirección")
                return f(*a)

        try:
            e = api.estado(url)
            # Evita mezclar datos reales y simulados
            if bool(e.get("simulada")) != (self.base.tipo == "simulado"):
                raise api.RespuestaInvalida(f"Esta base solo acepta macetas de tipo {self.base.tipo}")
            ahora = self.reloj()

            def anotar():
                self.vivo, self.ultimo, self.error = e, ahora, None
                self.base.contacto(self.did, ahora)
            si_vigente(anotar)

            if self.t_intento_hist is None or not 0 <= ahora - self.t_intento_hist < T_HISTORIAL:
                si_vigente(setattr, self, "t_intento_hist", ahora)
                si_vigente(self.base.guardar_config, self.did, api.config(url), self.reloj())
                r = api.historial(url, self.rango())

                def guardar():
                    n = self.base.guardar_historial(self.mid, self.did, r, self.reloj())
                    self.t_hist = self.reloj()
                    log.info("%s: %d lecturas nuevas", url, n)
                si_vigente(guardar)
            if self.t_diario is None or not 0 <= ahora - self.t_diario < T_DIARIO:
                si_vigente(setattr, self, "t_diario", ahora)
                si_vigente(self.base.guardar_diario, self.mid, self.did, api.diario(url))
            return True
        except (api.SinConexion, api.RespuestaInvalida) as ex:
            self.error = str(ex)
            return False

    @property
    def conectada(self):
        return self.ultimo is not None and self.vivo is not None and self.reloj() - self.ultimo <= T_CONECTADA


class Ingesta:
    def __init__(self, base):
        self.base, self.vigilantes, self.parar = base, {}, threading.Event()
        self.candado = threading.Lock()

    def sincronizar(self):
        with self.candado:
            for m in self.base.macetas():
                if m["id"] not in self.vigilantes:
                    v = self.vigilantes[m["id"]] = Vigilante(self.base, m)
                    threading.Thread(target=self._bucle, args=(v,), daemon=True).start()

    def _bucle(self, v):
        while not self.parar.is_set():
            t = time.monotonic()
            try:
                v.ciclo()
            except Exception:
                v.error = "Error interno: revisa el registro del servidor"
                log.exception("Fallo consultando %s", v.url)
            self.parar.wait(max(1, T_ESTADO - (time.monotonic() - t)))
