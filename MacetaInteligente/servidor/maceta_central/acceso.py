"""Acceso desde otros equipos de la red. --red: abierto, para una red privada. --red --codigo: HTTPS y
código de un solo uso. En ambos los permisos son limitados. Del código solo se conserva en memoria un hash scrypt. El PC entra sin código; desde la red solo se
consulta un resumen sin datos técnicos y se trabaja con las fotos."""
import hashlib
import hmac
import ipaddress
import re
import secrets
import socket
import threading
import time
from urllib.parse import parse_qs

from fastapi import Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

DURA_S = 12 * 3600
INTENTOS, BLOQUEO_S = 5, 300
CODIGO_S, FALLOS_CODIGO = 600, 10   # vida del código y errores que lo anulan
COOKIE = "maceta_sesion"
FOTOS = re.compile(r"/api/v1/macetas/[^/]+/fotos(/[^/]+(/restaurar)?)?")
ALTA, MAX_ALTA = "/api/v1/macetas", 20   # agregar desde el celular, hasta 20 macetas reales
PERMISO_S, PERMISO_FALLOS, PERMISO_MAX = 120, 3, 5   # autorización para borrar: vida, errores y solicitudes por equipo
BORRAR = re.compile(r"/api/v1/macetas/[^/]+")
PEDIR = re.compile(r"/api/v1/macetas/[^/]+/autorizacion")
NO = "Código incorrecto o vencido. Crea otro en el PC."
CABECERAS = {
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
                               "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
    "X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(self), microphone=(), geolocation=()"}
VIVO = ("listo", "hum_pct", "luz_pct", "luz_lx", "temp_c", "indice", "estado", "estados", "estado_texto", "frase",
        "horas_sin_regar", "pers", "simulada")

PAGINA = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Entrar · Macetas inteligentes</title><link rel="icon" href="data:,"><style>:root{color-scheme:light dark}
body{font:18px/1.5 system-ui,sans-serif;max-width:22em;margin:12vh auto;padding:0 20px}
input,button{box-sizing:border-box;width:100%;font:inherit;padding:14px;border-radius:12px;border:1px solid #888;margin-top:10px}
input{font-size:26px;letter-spacing:.15em;text-align:center}button{background:#1f6b3a;color:#fff;border:0;font-weight:700}</style></head>
<body><h1>Macetas inteligentes</h1><form method="post" action="/entrar"><label for="c">Código que muestra el PC</label>
<input id="c" name="codigo" inputmode="numeric" autocomplete="off" maxlength="12" required autofocus><button>Entrar</button></form>
<p role="alert">@MSG@</p></body></html>"""


def pagina(msg="", estado=200):
    return HTMLResponse(PAGINA.replace("@MSG@", msg), estado)


def direccion_red():
    """IP de este PC en la red actual. No envía datos: solo pregunta qué interfaz se usaría."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 9))
            return s.getsockname()[0]
        except OSError:
            return None


def _hash(codigo, sal):
    return hashlib.scrypt(codigo, salt=sal, n=2**14, r=8, p=1)


def _sha(t):
    return hashlib.sha256(t.encode()).hexdigest()


class Acceso:
    def __init__(self, puerto, locales=("127.0.0.1", "::1"), huella_tls="", con_codigo=True):
        self.con_codigo = con_codigo
        self.puerto, self.locales, self.huella_tls = puerto, locales, huella_tls
        self.clave, self.sesiones, self.fallos = None, {}, {}
        self.permiso, self.pedidos, self.candado = None, {}, threading.Lock()

    def nuevo_codigo(self):
        """Se entrega una sola vez; aquí queda únicamente [sal, hash, vencimiento, errores]."""
        c, sal = f"{secrets.randbelow(10**8):08d}", secrets.token_bytes(16)
        self.clave = [sal, _hash(c.encode(), sal), time.time() + CODIGO_S, 0]
        return c

    def vigente(self):
        k = self.clave
        return k if k and k[2] > time.time() else None

    def activas(self):
        ahora = time.time()
        self.sesiones = {k: v for k, v in self.sesiones.items() if v > ahora}
        return len(self.sesiones)

    # ----- Autorización para borrar una maceta: el celular la pide y el código sale en el PC -----
    def pendiente(self):
        k = self.permiso
        return k if k and k["vence"] > time.time() else None

    def pedir_permiso(self, ip, mid, nombre):
        ahora = time.time()
        with self.candado:
            k = self.pendiente()
            if k and k["ip"] != ip:
                raise HTTPException(409, "El PC ya está atendiendo otra solicitud. Espera 2 minutos")
            self.pedidos = {i: t for i, v in self.pedidos.items() if (t := [x for x in v if x > ahora - 600])}
            if len(self.pedidos.get(ip, [])) >= PERMISO_MAX:
                raise HTTPException(429, "Demasiadas solicitudes. Espera 10 minutos")
            self.pedidos.setdefault(ip, []).append(ahora)
            self.permiso = {"ip": ip, "mid": mid, "nombre": nombre, "codigo": f"{secrets.randbelow(10**6):06d}",
                            "vence": ahora + PERMISO_S, "fallos": 0}

    def usar_permiso(self, ip, mid, dado):
        with self.candado:
            k = self.pendiente()
            if not k or k["ip"] != ip or k["mid"] != mid:
                raise HTTPException(403, "Pide antes la autorización; el código aparece en el PC")
            if not hmac.compare_digest(re.sub(r"\s", "", dado).encode(), k["codigo"].encode()):
                k["fallos"] += 1
                if k["fallos"] >= PERMISO_FALLOS:
                    self.permiso = None
                    raise HTTPException(403, "Código incorrecto. Se anuló: pide otro")
                raise HTTPException(403, "Código incorrecto")
            self.permiso = None     # un solo uso

    def es_local(self, p):
        # El Host evita que una web externa apunte su dominio a este PC
        if p.client.host in self.locales:
            return p.url.hostname in ("127.0.0.1", "localhost", "::1")
        # El mismo PC entrando por su IP de red: origen y destino de la conexión son iguales
        ip = (p.scope.get("server") or ("",))[0]
        return bool(self.locales) and p.client.host == ip == p.url.hostname

    def con_sesion(self, p):
        return self.sesiones.get(_sha(p.cookies.get(COOKIE, "")), 0) > time.time()

    async def entrar(self, p):
        ip, ahora = p.client.host, time.time()
        self.fallos = {k: v for k, v in self.fallos.items() if v[1] > ahora}
        if self.fallos.get(ip, (0, 0))[0] >= INTENTOS:
            return pagina("Demasiados intentos. Espera 5 minutos.", 429)
        datos = b""
        async for x in p.stream():
            datos += x
            if len(datos) > 200:
                return pagina(NO, 413)
        dado = re.sub(rb"\s", b"", parse_qs(datos).get(b"codigo", [b""])[0])
        # El intento se cuenta antes de comprobarlo: los envíos simultáneos no se saltan el límite
        n = self.fallos.get(ip, (0, 0))[0] + 1
        self.fallos[ip] = (n, ahora + BLOQUEO_S)
        if n > INTENTOS:
            return pagina("Demasiados intentos. Espera 5 minutos.", 429)
        k = self.vigente()
        if k:
            k[3] += 1
            bien = k[3] <= FALLOS_CODIGO and hmac.compare_digest(await run_in_threadpool(_hash, dado, k[0]), k[1])
            if self.clave is k and (bien or k[3] >= FALLOS_CODIGO):
                self.clave = None       # un solo uso, o demasiados errores
                if bien:
                    self.fallos.pop(ip, None)
                    self.activas()
                    t = secrets.token_urlsafe(32)
                    self.sesiones[_sha(t)] = ahora + DURA_S
                    r = RedirectResponse("/", 303)
                    r.set_cookie(COOKIE, t, max_age=DURA_S, httponly=True, secure=True, samesite="strict")
                    return r
        return pagina(NO, 401)

    async def atender(self, p, seguir):
        if self.es_local(p):
            return await seguir(p)
        p.state.remoto = True
        ruta = p.url.path
        if not self.con_codigo:
            try:    # entrar solo por IP: una web externa no puede apuntar su dominio a este PC
                ipaddress.ip_address(p.url.hostname or "")
            except ValueError:
                return JSONResponse({"detail": "No disponible"}, 403)
            if ruta in ("/entrar", "/salir"):
                return RedirectResponse("/", 303)
        elif ruta == "/entrar":
            return await self.entrar(p) if p.method == "POST" else pagina()
        api = ruta.startswith("/api/")
        if self.con_codigo and not self.con_sesion(p):
            if api:
                return JSONResponse({"detail": "Vuelve a entrar con un código del PC"}, 401)
            return RedirectResponse("/entrar", 303)
        # Sin la cabecera que pone la página, abrir la API a mano no muestra datos
        if (api and not ruta.endswith(".jpg") or ruta == "/salir") and p.headers.get("x-maceta") != "1":
            return JSONResponse({"detail": "No disponible"}, 403)
        if ruta == "/salir" and p.method == "POST":
            self.sesiones.pop(_sha(p.cookies.get(COOKIE, "")), None)
            r = JSONResponse({"ok": True})
            r.delete_cookie(COOKIE)
            return r
        permitida = (p.method in ("GET", "HEAD") or FOTOS.fullmatch(ruta) or (p.method == "DELETE" and BORRAR.fullmatch(ruta))
                     or (p.method == "POST" and (ruta == ALTA or PEDIR.fullmatch(ruta))))
        if not permitida:
            return JSONResponse({"detail": "Esto solo se puede hacer desde el PC del servidor"}, 403)
        return await seguir(p)


def remoto(p):
    return getattr(p.state, "remoto", False)


def revisar_alta(n, registradas):
    """Desde el celular: solo macetas reales, en el puerto web normal y nunca apuntando a este PC."""
    h = n.url.removeprefix("http://")
    try:
        mal = ipaddress.ip_address(h).is_loopback or h == direccion_red()
    except ValueError:
        mal = not h.endswith(".local")      # localhost o con puerto
    if n.origen == "simulado" or mal:
        raise HTTPException(403, "Desde el celular solo se agregan macetas reales, por su IP y sin puerto")
    if registradas >= MAX_ALTA:
        raise HTTPException(403, "Hay demasiadas macetas. Agrégala desde el PC del servidor")


def maceta_publica(m):
    """Lo mínimo para el celular: sin IP, identificadores del equipo, calibración ni diagnóstico."""
    m = {k: m[k] for k in ("id", "nombre", "especie", "origen", "conectada", "ultimo_contacto", "lecturas", "fotos",
                           "calidad", "vivo", "config") if k in m}
    if m.get("vivo"):
        m["vivo"] = {k: m["vivo"][k] for k in VIVO if k in m["vivo"]}
    if m.get("config"):
        m["config"] = {"umbrales": m["config"].get("umbrales", {})}
    return m


def lectura_publica(x):
    return {k: x[k] for k in ("t", "fuente_hora", "hum_pct", "luz_pct", "indice", "estado", "calidad")}


def capacidad_publica(d):
    return {**d, "config": {**d["config"], "red": "Red"}, "recursos": [{**r, "detalle": ""} for r in d["recursos"]]}


def registrar(app, acceso, permitido):
    def local(p: Request):
        if not acceso or not acceso.con_codigo or not acceso.es_local(p):
            raise HTTPException(403, "Esto solo se puede hacer desde el PC del servidor")

    def local_red(p: Request):
        if not acceso or not acceso.es_local(p):
            raise HTTPException(403, "Esto solo se puede hacer desde el PC del servidor")

    @app.get("/api/v1/acceso")
    def estado(p: Request):
        if not acceso:
            return {"red": False, "remoto": False}
        if remoto(p):
            return {"red": True, "remoto": True, "con_codigo": acceso.con_codigo}
        ip = direccion_red()
        return {"red": True, "remoto": False, "con_codigo": acceso.con_codigo,
                "url": f"{'https' if acceso.con_codigo else 'http'}://{ip}:{acceso.puerto}" if ip else None,
                "codigo_vigente": bool(acceso.vigente()), "sesiones": acceso.activas(), "huella": acceso.huella_tls}

    @app.post("/api/v1/acceso/codigo", dependencies=[Depends(permitido), Depends(local)])
    def codigo():
        return {"codigo": acceso.nuevo_codigo(), "segundos": CODIGO_S}

    @app.get("/api/v1/acceso/permiso", dependencies=[Depends(local_red)])
    def permiso():
        k = acceso.pendiente()
        return {"permiso": k and {"maceta": k["nombre"], "codigo": k["codigo"], "equipo": k["ip"], "segundos": int(k["vence"] - time.time())}}

    @app.delete("/api/v1/acceso/permiso", dependencies=[Depends(permitido), Depends(local_red)])
    def rechazar():
        with acceso.candado:
            k, acceso.permiso = acceso.permiso, None
            if k:       # quien fue rechazado espera 10 minutos
                acceso.pedidos[k["ip"]] = [time.time()] * PERMISO_MAX
        return {"ok": True}

    @app.post("/api/v1/acceso/cerrar", dependencies=[Depends(permitido), Depends(local)])
    def cerrar():
        acceso.clave, acceso.sesiones = None, {}
        return {"ok": True}

    @app.middleware("http")
    async def guardia(p: Request, seguir):
        r = await (acceso.atender(p, seguir) if acceso else seguir(p))
        r.headers.update(CABECERAS)
        if remoto(p):
            r.headers["Cache-Control"] = "no-store"
        return r
