"""Cliente de la API que ya publica el ESP32. Solo hace GET: nunca modifica la maceta."""
import http.client
import ipaddress
import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlsplit

MAX_BYTES = 2_000_000


class SinConexion(Exception):
    pass


class RespuestaInvalida(Exception):
    pass


def validar_url(u):
    """Solo direcciones de la red local, para que el servidor no consulte otros sitios."""
    u = u.strip().rstrip("/")
    if "://" not in u:
        u = "http://" + u
    try:
        p = urlsplit(u)
        puerto = p.port
    except ValueError as e:
        raise ValueError("Dirección no válida") from e
    h = (p.hostname or "").lower()
    if p.scheme != "http" or not h or p.path or p.query or p.fragment or p.username is not None:
        raise ValueError("Usa solo la dirección, por ejemplo http://192.168.1.50")
    try:
        ip = ipaddress.ip_address(h)
        local = ip.version == 4 and (ip.is_private or ip.is_loopback) and not ip.is_unspecified
    except ValueError:
        local = h == "localhost" or re.fullmatch(r"[a-z0-9-]+\.local", h) is not None
    if not local:
        raise ValueError("La dirección debe ser de la red local")
    return f"http://{h}" + (f":{puerto}" if puerto and puerto != 80 else "")


class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SinRedireccion())


def _pedir(url, ruta, espera):
    try:
        with _abridor.open(url + ruta, timeout=espera) as r:
            cuerpo = r.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        e.close()
        raise RespuestaInvalida(f"La maceta respondió {e.code}") from e
    except (OSError, http.client.HTTPException) as e:
        raise SinConexion("La maceta no responde") from e
    if len(cuerpo) > MAX_BYTES:
        raise RespuestaInvalida("Respuesta demasiado grande")
    try:
        d = json.loads(cuerpo)
    except ValueError as e:
        raise RespuestaInvalida("La respuesta no es JSON") from e
    if not isinstance(d, dict):
        raise RespuestaInvalida("La respuesta no tiene el formato esperado")
    return d


def _exigir(d, campos, ruta):
    faltan = [k for k in campos if k not in d]
    if faltan:
        raise RespuestaInvalida(f"{ruta}: faltan {', '.join(faltan)}")
    return d


def estado(url):
    return _exigir(_pedir(url, "/api/estado", 8), ["listo", "uptime_s", "hum_raw", "luz_raw", "hum_pct", "luz_pct",
                                                   "indice", "estado", "arranque"], "estado")


def config(url):
    return _exigir(_pedir(url, "/api/config", 8), ["umbrales", "calibracion"], "config")


def _entero(x):
    return isinstance(x, int) and not isinstance(x, bool)


def historial(url, rango):
    d = _exigir(_pedir(url, "/api/historial?rango=" + rango, 40), ["ahora", "uptime_s", "arranque", "datos"], "historial")
    filas = d["datos"]
    if not all(_entero(d[k]) for k in ("ahora", "uptime_s", "arranque")) or not isinstance(filas, list) or not all(
            isinstance(f, list) and len(f) == 9 and all(_entero(x) for x in f) and f[1] in (0, 1, 2) and 0 <= f[5] <= 5
            for f in filas):
        raise RespuestaInvalida("historial: filas con formato inesperado")
    return d


def diario(url):
    d = _exigir(_pedir(url, "/api/diario?dias=365", 40), ["campos", "dias"], "diario")
    if not isinstance(d["campos"], list) or not isinstance(d["dias"], list) or not all(
            isinstance(f, list) and len(f) == len(d["campos"]) and f and isinstance(f[0], str) for f in d["dias"]):
        raise RespuestaInvalida("diario: filas con formato inesperado")
    return d
