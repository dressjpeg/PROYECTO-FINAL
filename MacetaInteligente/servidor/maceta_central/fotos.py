"""Registro fotográfico por maceta: archivos en disco y datos en SQLite.
Cada foto se reescribe en JPEG sin metadatos, así que nunca conserva el GPS del celular."""
import hashlib
import io
import shutil
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from PIL import Image, ImageOps

MAX_BYTES = 12_000_000
MAX_PIXELES = 60_000_000
LADO, LADO_MINI = 1600, 320
BOGOTA = timezone(timedelta(hours=-5))
VENTANA_S = 900     # condiciones: la lectura más cercana, a 15 min como mucho

ESQUEMA = """
CREATE TABLE IF NOT EXISTS fotos(
  id TEXT PRIMARY KEY, maceta_id TEXT NOT NULL REFERENCES macetas(id),
  ruta TEXT NOT NULL, subida_en INTEGER NOT NULL, capturada_en INTEGER NOT NULL,
  fuente_fecha TEXT NOT NULL,     -- usuario | camara | exif | subida
  nota TEXT NOT NULL DEFAULT '', altura_cm REAL, hojas INTEGER,
  ancho INTEGER NOT NULL, alto INTEGER NOT NULL, bytes INTEGER NOT NULL,
  sha256 TEXT NOT NULL, borrada_en INTEGER);   -- con valor = en la papelera
CREATE UNIQUE INDEX IF NOT EXISTS foto_unica ON fotos(maceta_id, sha256) WHERE borrada_en IS NULL;
CREATE INDEX IF NOT EXISTS foto_fecha ON fotos(maceta_id, capturada_en);
"""


def iniciar(base):
    with base.con() as c:
        c.executescript(ESQUEMA)
    base.tablas_extra = ("fotos",)   # para borrar_maceta


def carpeta(base):
    return base.ruta.parent / "fotos" / base.tipo


def hay(base, mid):
    with base.con() as c:
        return c.execute("SELECT COUNT(*) FROM fotos WHERE maceta_id=?", (mid,)).fetchone()[0]


def archivar(base, mid):
    """Al borrar una maceta, sus imágenes pasan a respaldos/ en vez de perderse."""
    o = carpeta(base) / mid
    if o.exists():
        shutil.move(str(o), str(base.ruta.parent / "respaldos" / f"fotos-{mid}"))


def _fecha_exif(img):
    try:
        e = img.getexif().get_ifd(0x8769)
        t = datetime.strptime(str(e[0x9003]).strip("\x00 "), "%Y:%m:%d %H:%M:%S")
        z = str(e.get(0x9011, "")).strip("\x00 ")
        zona = datetime.strptime(z, "%z").tzinfo if z else BOGOTA
        return int(t.replace(tzinfo=zona).timestamp())
    except Exception:   # EXIF ausente o mal formado: la foto sigue siendo válida
        return None


def _fecha_valida(t, ahora):
    return t is not None and 946_684_800 <= t <= ahora + 3600


def _procesar(datos):
    try:
        img = Image.open(io.BytesIO(datos))
        if img.format not in ("JPEG", "PNG", "WEBP", "MPO"):
            raise HTTPException(415, "Usa una foto JPG, PNG o WebP")
        if img.width * img.height > MAX_PIXELES:
            raise HTTPException(413, "La foto tiene demasiados píxeles")
        fecha = _fecha_exif(img)
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGBA")
            fondo = Image.new("RGB", img.size, "white")
            fondo.paste(img, mask=img.getchannel("A"))
            img = fondo
        salidas = []
        for lado, calidad in ((LADO, 82), (LADO_MINI, 76)):
            x = img.copy()
            x.thumbnail((lado, lado))
            # Imagen nueva: sin EXIF, GPS ni comentarios
            limpia = Image.new("RGB", x.size)
            limpia.paste(x)
            b = io.BytesIO()
            limpia.save(b, "JPEG", quality=calidad, optimize=True)
            salidas.append((b.getvalue(), x.size))
        return fecha, salidas
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(415, "No es una foto JPG, PNG o WebP válida. Las HEIC de iPhone deben convertirse a JPG") from e


def guardar(base, mid, datos, cuando, camara, nota, altura, hojas):
    ahora = int(time.time())
    sha = hashlib.sha256(datos).hexdigest()
    exif, ((grande, (w, h)), (mini, _)) = _procesar(datos)
    if cuando is not None:
        if not _fecha_valida(cuando, ahora):
            raise HTTPException(422, "La fecha de la foto no es válida o está en el futuro")
        t, fuente = cuando, "usuario"
    elif camara:
        t, fuente = ahora, "camara"
    elif _fecha_valida(exif, ahora):
        t, fuente = exif, "exif"
    else:
        t, fuente = ahora, "subida"
    fid = str(uuid.uuid4())
    d = datetime.fromtimestamp(t, BOGOTA)
    rel = f"{mid}/{d:%Y}/{d:%m}/{fid}"
    g = carpeta(base) / f"{rel}.jpg"
    m = carpeta(base) / f"{rel}_m.jpg"
    try:
        g.parent.mkdir(parents=True, exist_ok=True)
        g.write_bytes(grande)
        m.write_bytes(mini)
        with base.con() as c:
            c.execute("INSERT INTO fotos VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)",
                      (fid, mid, rel, ahora, t, fuente, nota, altura, hojas, w, h, len(grande), sha))
    except Exception as e:
        g.unlink(missing_ok=True)
        m.unlink(missing_ok=True)
        if isinstance(e, sqlite3.IntegrityError):
            if "FOREIGN KEY" in str(e):
                raise HTTPException(404, "No existe esa maceta") from e
            raise HTTPException(409, "Esa foto ya está guardada en esta maceta") from e
        if isinstance(e, OSError):
            raise HTTPException(507, "No se pudo guardar la foto en el disco") from e
        raise
    return fid


def listar(base, mid, desde, hasta, papelera):
    with base.con() as c:
        fs = [dict(f) for f in c.execute(
            "SELECT id,subida_en,capturada_en,fuente_fecha,nota,altura_cm,hojas,ancho,alto,bytes FROM fotos WHERE maceta_id=? "
            "AND capturada_en BETWEEN ? AND ? AND (borrada_en IS NOT NULL)=? ORDER BY capturada_en, subida_en",
            (mid, desde, hasta, papelera))]
        for f in fs:
            t = f["capturada_en"]
            x = c.execute("SELECT t,hum_pct,luz_pct,indice,estado FROM lecturas WHERE maceta_id=? AND t BETWEEN ? AND ? "
                          "ORDER BY ABS(t-?) LIMIT 1", (mid, t - VENTANA_S, t + VENTANA_S, t)).fetchone()
            f["condiciones"] = dict(x) if x else None
        return fs


def registrar(app, bases, buscar, permitido):
    for b in bases:
        iniciar(b)

    @app.post("/api/v1/macetas/{mid}/fotos", status_code=201, dependencies=[Depends(permitido)])
    async def subir(mid: str, pedido: Request, cuando: int | None = Query(None), camara: bool = False,
                    nota: str = Query("", max_length=200), altura: float | None = Query(None, ge=0, le=300),
                    hojas: int | None = Query(None, ge=0, le=999)):
        b, _ = await run_in_threadpool(buscar, mid)
        datos = bytearray()
        async for parte in pedido.stream():
            datos += parte
            if len(datos) > MAX_BYTES:
                raise HTTPException(413, "La foto supera 12 MB")
        if not datos:
            raise HTTPException(422, "No llegó ninguna foto")
        return {"id": await run_in_threadpool(guardar, b, mid, bytes(datos), cuando, camara, nota.strip(), altura, hojas)}

    @app.get("/api/v1/macetas/{mid}/fotos")
    def ver(mid: str, desde: int = Query(0, ge=0, le=2**40), hasta: int = Query(2**40, ge=0, le=2**40), papelera: bool = False):
        return listar(buscar(mid)[0], mid, desde, hasta, papelera)

    @app.get("/api/v1/macetas/{mid}/fotos/{fid}/{tam}.jpg")
    def imagen(mid: str, fid: str, tam: str):
        b, _ = buscar(mid)
        with b.con() as c:
            f = c.execute("SELECT ruta FROM fotos WHERE id=? AND maceta_id=?", (fid, mid)).fetchone()
        if not f or tam not in ("grande", "mini"):
            raise HTTPException(404, "No existe esa foto")
        r = carpeta(b) / (f["ruta"] + (".jpg" if tam == "grande" else "_m.jpg"))
        if not r.is_file():
            raise HTTPException(404, "Falta el archivo de la foto")
        return FileResponse(r, media_type="image/jpeg", headers={"X-Content-Type-Options": "nosniff"})

    def mover(mid, fid, borrar):
        b, _ = buscar(mid)
        try:
            with b.con() as c:
                n = c.execute("UPDATE fotos SET borrada_en=? WHERE id=? AND maceta_id=? AND (borrada_en IS NULL)=?",
                              (int(time.time()) if borrar else None, fid, mid, borrar)).rowcount
        except sqlite3.IntegrityError as e:
            raise HTTPException(409, "Esa foto ya está guardada en esta maceta") from e
        if not n:
            raise HTTPException(404, "No existe esa foto")
        return {"ok": True}

    @app.delete("/api/v1/macetas/{mid}/fotos/{fid}", dependencies=[Depends(permitido)])
    def a_papelera(mid: str, fid: str):
        return mover(mid, fid, True)

    @app.post("/api/v1/macetas/{mid}/fotos/{fid}/restaurar", dependencies=[Depends(permitido)])
    def restaurar(mid: str, fid: str):
        return mover(mid, fid, False)
