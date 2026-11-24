# Servidor central

Consulta cada maceta por su API actual (solo lectura) y guarda el historial en SQLite. No cambia el firmware.

## Usar (Windows, desde esta carpeta)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m maceta_central
```
Abre `http://127.0.0.1:8000`. Por ahora solo responde en este PC: para verlo en el celular falta una contraseña.

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
| `GET /api/v1/salud` | Comprueba el servidor |
| `GET /api/v1/macetas` | Macetas, conexión y último estado |
| `POST /api/v1/macetas` | JSON: nombre, url; opcionales: especie y origen (`real` o `simulado`) |
| `GET /api/v1/macetas/{id}` | Una maceta, con umbrales y calibración |
| `PATCH /api/v1/macetas/{id}/direccion` | JSON: url |
| `GET /api/v1/macetas/{id}/lecturas?desde=&hasta=&limite=` | Lecturas con hora (epoch UTC) |
| `GET /api/v1/macetas/{id}/diario` | Resumen por día |

POST, PUT y PATCH exigen `X-Maceta: 1`.

| `GET /api/v1/capacidad` | Conectadas, registradas, capacidad, cupo y límites (solo macetas reales) |
| `PUT /api/v1/capacidad` | JSON: red, limite_wifi, otros_equipos, anios |

Capacidad = el menor de los límites de WiFi, servidor y disco. Para medir el servidor en este PC: `.venv\Scripts\python -m simulador.prueba_carga` (unos 4 min; cierra antes el servidor).

## Reglas
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
