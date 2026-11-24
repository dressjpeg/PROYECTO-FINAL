# Servidor central

Consulta cada maceta por su API actual (solo lectura) y guarda el historial en SQLite. No cambia el firmware.

## Usar (Windows, desde esta carpeta)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m maceta_central
```
Por ahora solo responde en este PC (`http://127.0.0.1:8000/api/v1/macetas`). Aún no tiene dashboard.

Maceta virtual y, en otra terminal, el servidor con su base aparte:
```powershell
.venv\Scripts\python -m simulador.maceta_virtual --puerto 8101 --escenario sed
.venv\Scripts\python -m maceta_central --simulado --puerto 8001
```
Escenarios: `sana`, `sed`, `encharcada`, `poca_luz`.

## API
| Ruta | Qué hace |
|---|---|
| `GET /api/v1/salud` | Comprueba el servidor |
| `GET /api/v1/macetas` | Macetas, conexión y último estado |
| `POST /api/v1/macetas` | JSON: nombre, url, especie (opcional) |
| `GET /api/v1/macetas/{id}` | Una maceta |
| `PATCH /api/v1/macetas/{id}/direccion` | JSON: url |
| `GET /api/v1/macetas/{id}/lecturas?desde=&hasta=&limite=` | Lecturas con hora (epoch UTC) |
| `GET /api/v1/macetas/{id}/diario` | Resumen por día |

POST y PATCH exigen `X-Maceta: 1`.

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
