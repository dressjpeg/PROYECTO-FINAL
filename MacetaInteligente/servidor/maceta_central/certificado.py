"""Certificado propio para HTTPS. Se crea una vez con OpenSSL (viene con Git) y la clave privada queda
en la carpeta del usuario de Windows, fuera del proyecto."""
import hashlib
import shutil
import ssl
import subprocess
import tempfile
import time
from pathlib import Path

CARPETA = Path.home() / ".maceta_central"
DIAS = 365
CONF = """[req]
distinguished_name=dn
x509_extensions=v3
prompt=no
[dn]
CN=Maceta central
[v3]
subjectAltName=DNS:maceta-central.local
extendedKeyUsage=serverAuth
basicConstraints=critical,CA:FALSE
"""


def _openssl():
    for x in (shutil.which("openssl"), r"C:\Program Files\Git\mingw64\bin\openssl.exe", r"C:\Program Files\Git\usr\bin\openssl.exe"):
        if x and Path(x).is_file():
            return x
    raise SystemExit("--red necesita OpenSSL para cifrar la conexión (viene con Git para Windows). No se abre sin cifrar.")


def _sirve(cert, clave):
    try:
        ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(cert, clave)
        return time.time() - cert.stat().st_mtime < (DIAS - 7) * 86400
    except (OSError, ssl.SSLError):
        return False


def obtener(carpeta=CARPETA):
    """(certificado, clave, huella SHA-256)"""
    cert, clave = carpeta / "cert.pem", carpeta / "clave.pem"
    if not _sirve(cert, clave):
        carpeta.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as t:
            c = Path(t) / "c.cnf"
            c.write_text(CONF, encoding="ascii")
            r = subprocess.run([_openssl(), "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256", "-days", str(DIAS),
                                "-config", str(c), "-keyout", str(clave), "-out", str(cert)], capture_output=True, timeout=60)
        if r.returncode or not _sirve(cert, clave):
            raise SystemExit("No se pudo crear el certificado. No se abre sin cifrar.")
    d = hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text())).hexdigest().upper()
    return cert, clave, ":".join(d[i:i + 2] for i in range(0, 64, 2))
