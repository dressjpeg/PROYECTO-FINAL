# Maceta inteligente: dashboard web

## Configurar el WiFi
1. Abre `secrets.h` (si no existe, copia `secrets.example.h` con ese nombre).
2. Escribe el nombre y la clave de una red de **2,4 GHz**. El ESP32 no usa 5 GHz.
3. Compila con la placa «ESP32 Dev Module» y sube por USB. No compartas `secrets.h`.

## Abrir el dashboard
Con el celular en la misma red: `http://maceta.local` o la IP que sale 5 s en el LCD y por serie (`# Dashboard: ...`).
Si `maceta.local` no abre, usa la IP. Algunas redes (universidad, invitados) aíslan los equipos: usa el hotspot del celular.
El primer arranque tarda unos segundos más porque formatea LittleFS.
Para apagar el WiFi: `#define DASH_WIFI_ON 0` en `Dashboard.ino`.

El WiFi transmite a 8,5 dBm (`DASH_POTENCIA_WIFI`): con la potencia normal titilaba la luz del LCD al alimentar la maceta desde el PC. Si la maceta queda lejos del router y falla la conexión, súbela a `WIFI_POWER_15dBm`.

## Cambios al .ino principal (solo 3 líneas)
| Dónde | Línea |
|---|---|
| `setup()`, después de `linea(1, "Leyendo...")` | `dashboardIniciar();` |
| Primera línea de `loop()` | `dashboardAtender();` |
| Última línea de `loop()` | `dashboardRegistrar();` |

## API
| Ruta | Campos o parámetros |
|---|---|
| `GET /` | Página |
| `GET /api/estado` | listo, uptime_s, hum_raw, luz_raw, hum_pct, luz_pct, indice, estado, estado_texto, frase, horas_sin_regar, avisos[] (estado, clave, texto, frase), alertas[] (estado, clave, texto, desde_s = segundos activa, inicio), resueltas[] (estado, clave, texto, inicio, fin, duracion_s), wifi_rssi, ip, hora_real, epoch, fs_ok, fs_usado, fs_total, heap_libre, heap_min, arranque, estados[] (todos los avisos activos, o [4] / [5]), pers |
| `GET /api/config` | umbrales, calibracion, tiempos, personalidad |
| `GET /api/historial?rango=1h\|24h\|7d` | hora_real, ahora, uptime_s, arranque, campos[], datos[][]: t, hora, hum_pct, luz_pct, indice, estado, hum_raw, luz_raw, arranque |
| `GET /api/historial.csv` | Descarga de todo el historial |
| `POST /api/riego` | Reinicia tUltimoRiego |
| `GET /api/crecimiento` | max, registros[] (id, fecha, altura, hojas, nota) |
| `POST /api/crecimiento` | Formulario: fecha (AAAA-MM-DD), altura (0–300), hojas (0–999), nota (máx. 60) |
| `DELETE /api/crecimiento?id=N` | Borra un registro |
| `GET /api/crecimiento.csv` | Descarga |
| `GET /api/diario?dias=30\|90\|365` | campos[], dias[][], hoy_parcial[]: fecha, hum_prom/min/max, luz_prom/min/max, indice_prom, riegos, min_sed, min_encharcada, min_poca_luz, min_mucha_luz, min_estresada, muestras |
| `GET /api/diario.csv` | Descarga |

POST y DELETE exigen la cabecera `X-Maceta: 1`. No hay contraseña: cualquiera en tu red puede usar la página.
`hora`: 0 = sin hora (t es uptime), 1 = hora real, 2 = corregida con NTP del mismo arranque. `inicio` o `fin` = 0: sin hora real.
Los CSV usan `;` y coma decimal (Excel en español).

## Cómo interpretar los datos
- **Medido por sensor:** humedad y luz. **Estimado por reglas:** índice y estado. **Registrado a mano:** altura y hojas.
- Los minutos de alerta del diario cuentan desde el aviso confirmado (5 s). El banner espera 10 min (agua) o 30 min (las demás).
- Al reiniciar empiezan de cero las horas sin regar y las alertas en curso; historial, crecimiento, diario y resueltas se conservan. Del día se puede perder hasta 1 h.
- Riegos a menos de 5 min entre sí cuentan como uno. Un riego marcado a mano también cuenta.
- Sin internet no hay fecha real: el resumen queda como `sin_hora` y no entra en «Crecimiento vs. condiciones».
- Las mediciones nuevas se ven en pocos segundos; el estado tarda además los 5 s de `T_CONFIRMAR`.
- La noche también cuenta como POCA_LUZ, porque así funcionan las reglas del firmware.

## Límites de almacenamiento
Historial: 8 archivos de 288 lecturas (máx. 2304, ~50 KB; siempre quedan 7 días de lecturas). Crecimiento: 500 registros. Diario: 400 días. Alertas resueltas: 10.
