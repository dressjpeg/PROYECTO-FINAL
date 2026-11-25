# Maceta inteligente

Proyecto final de Adquisición de Datos (IUE). Un ESP32 mide la humedad del suelo y la luz, estima el estado de una planta con reglas (sin IA) y lo muestra en un LCD 16x2 y en un dashboard web local.

| Tipo de dato | Variables |
|---|---|
| Medido por sensor | Humedad del suelo (sensor resistivo YL-69) y luz (LDR) |
| Estimado por reglas | Índice de salud y estado |
| Registrado a mano | Altura y número de hojas |

El índice de salud es una estimación, no una medición.

## Contenido
| Carpeta | Qué hay |
|---|---|
| `MacetaInteligente/maceta_inteligente/` | Firmware v3 y dashboard web ([guía y API](MacetaInteligente/maceta_inteligente/LEEME.md)) |
| `MacetaInteligente/MacetaInteligente_v3_backup.ino` | Firmware v3 antes del dashboard |
| `MacetaInteligente/servidor/` | Servidor central en desarrollo ([guía](MacetaInteligente/servidor/LEEME.md)) |
| `MacetaInteligente/avatar/` | Avatar animado original (integrado en la primera pestaña del dashboard) |
| `Documentos/` | Roadmap, objetivos y alcance, lista de compras |
| `Bocetos Visuales/` | Bocetos e infografía conceptuales |

Los documentos y bocetos describen ideas iniciales; algunos componentes difieren del firmware actual.

## Compilar
1. Arduino IDE con el core esp32 de Espressif 3.3.12, placa «ESP32 Dev Module» y la librería LiquidCrystal I2C de Frank de Brabander.
2. En `MacetaInteligente/maceta_inteligente/`, copia `secrets.example.h` como `secrets.h` y escribe tu red de 2,4 GHz.
3. Abre `maceta_inteligente.ino`, compila y sube.
