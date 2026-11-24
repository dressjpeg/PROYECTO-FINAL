# Servidor central

Consulta cada maceta por su API actual (solo lectura) y guarda el historial en SQLite. No cambia el firmware.

## Usar (Windows, desde esta carpeta)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m maceta_central
```
Abre `http://127.0.0.1:8000`. Sin `--red` solo responde en este PC.

### Desde el celular
```powershell
.venv\Scripts\python -m maceta_central --demo --red
```
Conecta el PC al hotspot del celular; en el PC, «Abrir en el celular» muestra la dirección (`http://IP-del-PC:8000`). Ábrela en el celular: no pide código.

Entra cualquiera que esté en esa red y la conexión no va cifrada, aparte del cifrado del WiFi: úsalo solo en tu hotspot o red privada, nunca en una WiFi pública. Desde la red solo se consulta y se manejan las fotos. No se entregan IP, identificadores del equipo, calibración, diagnóstico ni nombre de la red, y la API no se puede abrir a mano.

Con `--red --codigo` se entra por HTTPS (puerto 8443) con un código de 8 dígitos que se crea en el PC: un solo uso, 10 min, guardado solo como hash scrypt en memoria; 5 errores bloquean ese equipo 5 min y 10 anulan el código. La sesión dura 12 h. El celular avisa que no conoce el certificado; compara su huella SHA-256 con la del PC. La clave privada queda en `%USERPROFILE%\.maceta_central`: no la compartas.

Si no abre, falta permitir el puerto (8000, u 8443 con código). En PowerShell **como administrador**, una sola vez:
```powershell
New-NetFirewallRule -DisplayName "Maceta central" -Direction Inbound -Protocol TCP -LocalPort 8000 -RemoteAddress LocalSubnet -Action Allow
```
Para quitarla: `Remove-NetFirewallRule -DisplayName "Maceta central"`.

### Con macetas simuladas
En una terminal el servidor y en otra las cuatro virtuales (se registran solas):
```powershell
.venv\Scripts\python -m maceta_central --demo
.venv\Scripts\python -m simulador.demo
```
En la segunda, `1` a `4` apaga o enciende una; `s` sale. Sus lux y temperatura también son simulados.
La maceta real muestra «Nivel de luz (%)» mientras no haya una calibración en lux.

## API
| Ruta | Qué hace |
|---|---|
| `GET /api/v1/acceso` | Si se permite entrar desde la red; el código solo se entrega al PC |
| `GET /api/v1/salud` | Comprueba el servidor |
| `GET /api/v1/macetas` | Macetas, conexión y último estado |
| `POST /api/v1/macetas` | JSON: nombre, url; opcionales: especie y origen (`real` o `simulado`) |
| `GET /api/v1/macetas/{id}` | Una maceta, con umbrales y calibración |
| `PATCH /api/v1/macetas/{id}/direccion` | JSON: url |
| `DELETE /api/v1/macetas/{id}?nombre=` | Borra la maceta y sus datos; si tiene lecturas exige el nombre exacto |
| `GET /api/v1/macetas/{id}/lecturas?desde=&hasta=&limite=` | Lecturas con hora (epoch UTC) |
| `GET /api/v1/macetas/{id}/diario` | Resumen por día |

POST, PUT, PATCH y DELETE exigen `X-Maceta: 1`.

| `GET /api/v1/macetas/{id}/fotos?desde=&hasta=&papelera=` | Fotos en orden, con las condiciones más cercanas |
| `POST /api/v1/macetas/{id}/fotos?cuando=&camara=&nota=&altura=&hojas=` | El cuerpo es la imagen (JPG, PNG o WebP, máx. 12 MB) |
| `GET /api/v1/macetas/{id}/fotos/{foto}/grande.jpg` o `mini.jpg` | Imagen |
| `DELETE /api/v1/macetas/{id}/fotos/{foto}` y `POST …/restaurar` | Enviar a la papelera y recuperar |
| `GET /api/v1/capacidad` | Conectadas, registradas, capacidad, cupo y límites (solo macetas reales) |
| `PUT /api/v1/capacidad` | JSON: red, limite_wifi, otros_equipos, anios |

Capacidad = el menor de los límites de WiFi, servidor y disco. Para medir el servidor en este PC: `.venv\Scripts\python -m simulador.prueba_carga` (unos 4 min; cierra antes el servidor).

## Reglas
- Fotos: se guardan a 1600 px y 320 px en `datos/fotos/`, sin metadatos ni GPS. `fuente_fecha`: `usuario`, `camara`, `exif` o `subida`. Altura y hojas de la foto se escriben a mano y son independientes de `/api/crecimiento` de la maceta. Al borrar una maceta, sus imágenes pasan a `datos/respaldos/`.
- Respaldo: copia la carpeta `datos/` con el servidor cerrado.
- Antes de borrar una maceta se copia la base completa en `datos/respaldos/`. Para recuperarla: cierra el servidor y reemplaza el `.db` (quita también los `-wal` y `-shm`); se pierde lo guardado después de la copia.
- `simulador.demo` vuelve a registrar sus cuatro macetas al iniciar, aunque se hayan borrado.
- Estado cada 10 s; historial cada 5 min; diario cada hora. Tras un corte recupera hasta 7 días de la maceta.
- `conectada`: respondió en los últimos 30 s.
- `fuente_hora`: `real` (NTP de la maceta), `corregida` (la maceta la recalculó), `servidor` (hora del PC), `sin_hora`.
- Los datos reales y simulados van en archivos distintos, y cada base rechaza el otro tipo.
- `calibracion_id` es la calibración vigente al recibir la lectura.
- El servidor no puede comprobar qué ESP32 responde en una dirección, porque el prototipo 1 no publica un ID.
- Aún no copia `/api/crecimiento` ni las alertas resueltas: siguen en la maceta y sus CSV.

## Pruebas
```powershell
.venv\Scripts\python -m pytest -q
```
