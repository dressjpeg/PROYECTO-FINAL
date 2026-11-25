"""Cuántas macetas reales caben. Cada recurso dice su límite y de dónde sale la cifra.
Las simuladas corren en el PC: no ocupan cupos de WiFi ni entran en el cálculo."""
import json
import shutil
from pathlib import Path

LECTURAS_ANIO = 105_120          # una cada 5 min
MB_FOTOS_ANIO = 155              # una foto diaria de ~425 KB (estimado)
BYTES_LECTURA = 130              # estimado, hasta tener 1000 lecturas guardadas
# otros_equipos: los que ocupan cupo sin ser macetas (el PC; no el celular que comparte)
INICIAL = {"red": "Hotspot del celular", "limite_wifi": None, "otros_equipos": 1, "anios": 3}


def leer_config(base):
    with base.con() as c:
        f = c.execute("SELECT valor FROM meta WHERE clave='capacidad'").fetchone()
    return {**INICIAL, **(json.loads(f[0]) if f else {})}


def guardar_config(base, d):
    with base.con() as c:
        c.execute("INSERT INTO meta VALUES('capacidad',?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
                  (json.dumps(d),))


def _carga(base):
    try:
        d = json.loads((base.ruta.parent / "carga.json").read_text(encoding="utf-8"))
        bien = [n["macetas"] for n in d["niveles"] if n["ok"]]
        return (max(bien), d["fecha"]) if bien else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _bytes_lectura(bases):
    """Medido en la base más llena: incluye índices."""
    mejor = None
    for b in bases:
        with b.con() as c:
            n = c.execute("SELECT COUNT(*) FROM lecturas").fetchone()[0]
            tam = c.execute("PRAGMA page_count").fetchone()[0] * c.execute("PRAGMA page_size").fetchone()[0]
        if n >= 1000 and (mejor is None or n > mejor[0]):
            mejor = (n, tam / n)
    return mejor[1] if mejor else None


def calcular(bases, conectadas, registradas, latencias):
    base, cfg = bases[0], leer_config(bases[0])
    rec = []
    if cfg["limite_wifi"] is None:
        rec.append({"clave": "wifi", "nombre": "Red WiFi", "limite": None, "origen": "sin dato",
                    "detalle": "Escribe cuántos equipos admite la red"})
    else:
        rec.append({"clave": "wifi", "nombre": "Red WiFi", "limite": max(0, cfg["limite_wifi"] - cfg["otros_equipos"]),
                    "origen": "configurado", "detalle": f"{cfg['red']}: admite {cfg['limite_wifi']} equipos y "
                    f"{cfg['otros_equipos']} no {'es maceta' if cfg['otros_equipos'] == 1 else 'son macetas'}"})
    q = _carga(base)
    rec.append({"clave": "servidor", "nombre": "Servidor y base de datos", "limite": q[0] if q else None, "al_menos": bool(q),
                "origen": "medido" if q else "sin dato", "fecha": q[1] if q else None,
                "detalle": "Prueba de carga en este PC con macetas simuladas; no mide el WiFi" if q
                else "Ejecuta la prueba de carga (ver LEEME)"})
    medido = _bytes_lectura(bases)
    mb = (medido or BYTES_LECTURA) * LECTURAS_ANIO / 1e6 + MB_FOTOS_ANIO
    libre = shutil.disk_usage(Path(base.ruta).parent).free / 1e6
    rec.append({"clave": "disco", "nombre": "Disco del PC", "limite": int(libre * 0.8 / (mb * cfg["anios"])), "origen": "estimado",
                "detalle": f"{libre / 1000:.0f} GB libres; ~{mb:.0f} MB por maceta al año (incluye una foto diaria) durante "
                f"{cfg['anios']} {'año' if cfg['anios'] == 1 else 'años'}"})
    conocidos = [r for r in rec if r["limite"] is not None]
    # Sin el dato del WiFi no hay capacidad: el resto no es el freno
    cap = min(r["limite"] for r in conocidos) if cfg["limite_wifi"] is not None else None
    lat = sorted(latencias)
    return {"conectadas": conectadas, "registradas": registradas, "capacidad": cap,
            "disponible": None if cap is None else max(0, cap - registradas),
            "excedida": cap is not None and registradas > cap,
            "limitante": None if cap is None else next(r["nombre"] for r in conocidos if r["limite"] == cap),
            "recursos": rec, "config": cfg,
            "latencia_p95_s": round(lat[min(len(lat) - 1, int(len(lat) * .95))], 3) if len(lat) >= 5 else None,
            "consultas_medidas": len(lat)}
