# Cómo correr la maceta inteligente

Última actualización: 24 de noviembre de 2026.

## Las tres partes
| Parte | Qué es | Dónde se abre |
|---|---|---|
| Maceta | El ESP32 con sus sensores | `http://maceta.local` o su IP |
| Servidor central | Programa del PC: jardín, historial y fotos | `http://127.0.0.1:8000` (en el PC) |
| Macetas simuladas | Programa opcional del PC para la presentación | Aparecen en el servidor |

La maceta funciona sola. El servidor también funciona con la maceta apagada: conserva el historial y las fotos.

## Arranque de cada día
Los comandos se escriben en PowerShell, desde la carpeta `MacetaInteligente\maceta_inteligente`.

### 1. Conecta todo a la misma red
Enciende el hotspot del celular (banda de **2,4 GHz**) y conecta el PC. El hotspot admite 6 equipos.

### 2. Enciende la maceta
La pantalla muestra su IP durante unos 5 s. Si cambió, actualízala en el paso 5.

### 3. Abre el servidor
```powershell
cd ..\servidor; .venv\Scripts\python -m maceta_central --demo --red
```
Deja esa ventana abierta. `--demo` permite macetas simuladas; `--red` permite entrar desde el celular.

| Quiero | Opciones al final del comando |
|---|---|
| Solo este PC y solo macetas reales | (ninguna) |
| Solo este PC, con simuladas | `--demo` |
| PC y celular, con simuladas | `--demo --red` |
| PC y celular, con código y HTTPS | `--demo --red --codigo` |

### 4. Enciende las simuladas (opcional)
En **otra** ventana, abierta en la misma carpeta del inicio:
```powershell
cd ..\servidor; .venv\Scripts\python -m simulador.demo
```
Teclas `1` a `4` y Enter: apagan o encienden una. `s` y Enter: salir. Al iniciar vuelve a registrar sus cuatro macetas aunque se hayan borrado.

### 5. Abre el dashboard
- **PC:** `http://127.0.0.1:8000`
- **Celular:** en el PC despliega «Abrir en el celular» y escribe en el celular esa dirección, con `http://`. No pide código.
- **Si cambió la IP de la maceta:** en el PC, entra a la maceta → «Conexión» → «Cambiar dirección».

### Para cerrar
`Ctrl+C` en la ventana del servidor y `s` en la de las simuladas. No se pierde lo guardado.

## Tomar la foto
Maceta → «Fotos del crecimiento» → «Tomar foto» o «Subir fotos». Usa siempre el mismo ángulo y deja la regla visible. Se aceptan JPG, PNG y WebP de hasta 12 MB; las HEIC de iPhone se convierten antes a JPG.

## Instalar por primera vez en un PC
Hace falta Python 3.11 e internet:
```powershell
cd ..\servidor
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
```
`--codigo` necesita además Git para Windows (trae OpenSSL).

## Cambiar la red WiFi de la maceta
1. Escribe la red de 2,4 GHz y su clave en `secrets.h` (si no existe, copia `secrets.example.h`). No lo compartas.
2. Abre `maceta_inteligente.ino` en Arduino IDE: core esp32 3.3.12, placa «ESP32 Dev Module» y librería LiquidCrystal I2C de Frank de Brabander.
3. Compila y sube por USB.

## Si algo falla
| Problema | Qué hacer |
|---|---|
| No se reconoce `.venv` | Estás en otra carpeta. Vuelve a `maceta_inteligente` y copia el comando completo |
| El puerto 8000 está en uso | El servidor ya está abierto en otra ventana: úsalo o ciérralo con `Ctrl+C` |
| El celular no abre la página | Revisa la misma red, `http://` y la dirección que muestra el PC. Si usas el router, apaga los datos móviles; si el celular es el hotspot, déjalos encendidos |
| Sigue sin abrir | Permite Python en el firewall de Windows (regla en `servidor\LEEME.md`) |
| La maceta sale «Sin conexión» | Revisa que esté encendida, en la misma red y con la IP correcta (paso 5). Al volver, se recuperan hasta 7 días de historial |
| `maceta.local` no abre | Usa la IP |
| La página se ve vieja | Recarga con `Ctrl+F5` |

## Seguridad y respaldo
- Usa `--red` solo en tu hotspot o red privada: sin código entra cualquiera de esa red, y la página propia de la maceta no tiene contraseña.
- Respaldo: con el servidor cerrado, copia la carpeta `servidor\datos`.
- No publiques `secrets.h`, los `.bin`, `servidor\datos` ni `%USERPROFILE%\.maceta_central`.

## Comprobar que todo está bien
```powershell
cd ..\servidor; .venv\Scripts\python -m pytest -q
```
Debe decir `54 passed`.

## Cambios en la forma de correrlo
| Fecha | Cambio |
|---|---|
| 24-nov-2026 | Primera versión: servidor, simuladas, fotos y acceso desde el celular sin código |
