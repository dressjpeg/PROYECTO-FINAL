# Recalibración de humedad y luz

**Estado: pendiente.** Se hace con la maceta final impresa y ensamblada, el sustrato y la luz reales. Las casillas vacías se llenan con mediciones propias; no se inventan ni se copian del simulador.

## Valores actuales del firmware (`prototipo-1`)
| Constante | Valor | Origen |
|---|---|---|
| `HUM_SECO` | 4095 | Medido: sonda al aire |
| `HUM_HUMEDO` | 1620 | Medido antes en agua; **no se repitió** el 24-nov |
| `LUZ_OSCURO_LOG` | 4000 | Elegido como casi oscuro |
| `LUZ_CLARO_LOG` | 30 | **Provisional: estimado**, no medido al sol |

Medido el 24-nov-2026: aire 4095 (0 %); agua 2170–2320 (71–78 %). Con esos valores «Encharcada» (más de 85 %) pide una lectura cruda de unos 1966 o menos, así que no aparece.

Los dos sensores **bajan** su lectura con más agua o más luz. El YL-69 es resistivo: cambia con las sales, la profundidad, la compactación y la corrosión. Su porcentaje es relativo a esta calibración, no contenido de agua en volumen.

## 1. Materiales
- [ ] Maceta final ensamblada, con la sonda y la LDR en su posición definitiva
- [ ] El mismo sustrato, en dos recipientes aparte: uno seco y otro para saturar
- [ ] Agua de riego habitual, vaso medidor y recipiente con agujeros de drenaje
- [ ] Marca en la sonda para repetir siempre la misma profundidad (sin mojar la placa ni los pines)
- [ ] Paño limpio, tapa opaca o cartón y la lámpara real
- [ ] PC, cable USB y reloj

No satures la maceta con la planta: usa el recipiente aparte, sin planta.

## 2. Antes de empezar
- [ ] Guardar el código en git y anotar el commit: ____________
- [ ] Descargar de la maceta `/api/historial.csv`, `/api/crecimiento.csv` y `/api/diario.csv`
- [ ] Copiar `servidor\datos` con el servidor cerrado
- [ ] Confirmar 3,3 V en los sensores y cables firmes
- [ ] Dejar la maceta encendida 10 min
- [ ] Anotar inicio (fecha y hora): ____________ . Lo medido desde aquí hasta el fin es **prueba**, no comportamiento de la planta

## 3. Cómo tomar cada lectura
1. Coloca la sonda a la misma profundidad. Limpia y seca los dientes entre condiciones.
2. Espera 2 min, o hasta que deje de subir o bajar de forma continua.
3. Anota **10 lecturas crudas, una cada 10 s**, desde «Datos técnicos» del dashboard o el monitor serie a 115200 (`hum_raw` y `luz_raw` son las dos primeras columnas).
4. Saca y vuelve a poner la sonda; repite. Son **3 repeticiones** por condición.
5. Calcula la mediana de cada repetición y la mediana de las tres.

Si mínimo y máximo de una repetición difieren más de 100 cuentas, revisa cables y contacto, y repite. Ese límite es un criterio práctico del proyecto.

## 4. Humedad (`hum_raw`)
| Condición | Rep. | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 | L10 | Mediana | Mín–máx |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A. Aire, limpia y seca (control) | 1 | | | | | | | | | | | | |
| | 2 | | | | | | | | | | | | |
| | 3 | | | | | | | | | | | | |
| B. Sustrato seco | 1 | | | | | | | | | | | | |
| | 2 | | | | | | | | | | | | |
| | 3 | | | | | | | | | | | | |
| C. Humedad adecuada para la planta | 1 | | | | | | | | | | | | |
| | 2 | | | | | | | | | | | | |
| | 3 | | | | | | | | | | | | |
| D. Regado y drenado 30 min | 1 | | | | | | | | | | | | |
| | 2 | | | | | | | | | | | | |
| | 3 | | | | | | | | | | | | |
| E. Saturado, con agua visible | 1 | | | | | | | | | | | | |
| | 2 | | | | | | | | | | | | |
| | 3 | | | | | | | | | | | | |

Agua usada en C: ____ ml · D: ____ ml · E: ____ ml · Sustrato: ____________

**Propuesta:** `HUM_SECO` = mediana de B: ______ · `HUM_HUMEDO` = mediana de E: ______

`hum_pct = (HUM_SECO − raw) × 100 / (HUM_SECO − HUM_HUMEDO)`, limitado entre 0 y 100.

| Condición | Mediana cruda | % con la propuesta | Debe cumplir | ¿Cumple? |
|---|---|---|---|---|
| B. Seco | | | Menos de 30 % (Seca) | |
| C. Adecuada | | | 40–75 % (puntaje completo del índice) | |
| D. Drenado | | | No más de 85 % (no Encharcada) | |
| E. Saturado | | | Más de 85 % en las tres repeticiones | |

Además, las medianas deben ir en orden B > C > D > E y los rangos mín–máx de D y E no deben traslaparse. **Si no cumple, no fuerces los números:** revisa profundidad, contacto y sonda, y repite. Si D y E no se distinguen, el sensor no detecta de forma fiable el encharcamiento: se documenta como limitación antes de decidir si se tocan umbrales. Si B lee 4095, está en el tope del ADC y más seco ya no se distingue.

## 5. Luz (`luz_raw`)
Con la LDR en su posición final y sin sombra de la mano. Mismo método: 10 lecturas y 3 repeticiones; entre repeticiones retira y vuelve a poner la tapa o la lámpara.

| Condición | Rep. | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 | L10 | Mediana | Mín–máx |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F. Tapada, casi oscuro | 1 | | | | | | | | | | | | |
| | 2 | | | | | | | | | | | | |
| | 3 | | | | | | | | | | | | |
| G. Luz insuficiente | 1 | | | | | | | | | | | | |
| | 2 | | | | | | | | | | | | |
| | 3 | | | | | | | | | | | | |
| H. Lugar habitual, de día | 1 | | | | | | | | | | | | |
| | 2 | | | | | | | | | | | | |
| | 3 | | | | | | | | | | | | |
| I. Lámpara de la presentación | 1 | | | | | | | | | | | | |
| | 2 | | | | | | | | | | | | |
| | 3 | | | | | | | | | | | | |
| J. Sol directo, despejado | 1 | | | | | | | | | | | | |
| | 2 | | | | | | | | | | | | |
| | 3 | | | | | | | | | | | | |

Hora y cielo en J: ____________ . Mide unos minutos, sin exponer la electrónica ni el LCD.

**Propuesta:** `LUZ_OSCURO_LOG` = mediana de F: ______ · `LUZ_CLARO_LOG` = mediana de J: ______

- `LUZ_OSCURO_LOG` debe ser menor que 4095 y `LUZ_CLARO_LOG` mayor que 0; si no, la fórmula falla. Debe cumplirse oscuro > claro.
- Si F da 4095, conserva 4000. Si J da 0 o no hubo sol directo, conserva 30 y sigue llamándolo provisional.

Con `r = raw / (4095 − raw)`: `luz_pct = 100 × ln(r_oscuro / r) / ln(r_oscuro / r_claro)`, limitado entre 0 y 100.

| Condición | Mediana cruda | % con la propuesta | Debe cumplir | ¿Cumple? |
|---|---|---|---|---|
| F. Oscuro | | | Menos de 20 % (Poca luz) | |
| G. Insuficiente | | | Menos de 20 % | |
| H. Habitual | | | 30–80 % (puntaje completo del índice), si ese lugar es bueno para la planta | |
| I. Lámpara | | | Se anota; debe quedar entre F y J | |
| J. Sol directo | | | Más de 90 % (Mucha luz) | |

Sin luxómetro, la luz es nivel relativo en %, no lux.

## 6. Cambio en el firmware (solo con autorización explícita)
En `maceta_inteligente.ino`, sección «Calibracion»: `HUM_SECO`, `HUM_HUMEDO`, `LUZ_OSCURO_LOG`, `LUZ_CLARO_LOG`. No cambia nada más.

Los umbrales (30, 85, 20, 90 y 70), `SALTO_RIEGO` (15) y los tramos del índice (40–75 y 30–80) **no se tocan primero**; un cambio ahí exige justificación aparte.

1. Compila y sube por USB, con **Erase All Flash: Disabled** para no borrar los datos de la maceta.
2. Comprueba en «Datos técnicos» que aparezcan los cuatro valores nuevos. El servidor asocia la calibración nueva a las lecturas siguientes.
3. Las lecturas anteriores conservan el porcentaje viejo: no se comparan con las nuevas como si fueran la misma escala.

## 7. Validación final
Con la maceta real y **sin** usar las lecturas de las secciones 4 y 5:
- [ ] Tres mediciones nuevas por condición B, C, D y E: estado correcto en ____ de 12
- [ ] Tres mediciones nuevas por condición F, G y J: estado correcto en ____ de 9
- [ ] Cada cambio aparece después de unos 5 s de confirmación, en el LCD y el dashboard
- [ ] Un riego real se detecta (la humedad sube 15 puntos o más en una ventana de 10 s) y reinicia «Sin regar». Si el agua se reparte más lento, puede no detectarse: anótalo
- [ ] 24 h en la maceta final sin saltos inexplicables
- [ ] Historial, fotos y celular siguen funcionando

Se acepta si acierta todo. Si no, anota qué falló y no lo presentes como validado. Fin (fecha y hora): ____________

## 8. Volver a `prototipo-1`
Antes, anota los valores nuevos: esto descarta los cambios sin guardar de ese archivo. Desde `maceta_inteligente`:
```powershell
git restore --source prototipo-1 -- maceta_inteligente.ino
```
Abre el `.ino` en Arduino IDE (core esp32 3.3.12, «ESP32 Dev Module»), compila y sube con **Erase All Flash: Disabled**. Comprueba que vuelvan 4095 / 1620 / 4000 / 30.

No uses el `.merged.bin` de `respaldos`: cubre toda la memoria y puede borrar historial, crecimiento y diario. Los `.bin` contienen la clave WiFi: no los compartas.

## Resultado
| Constante | Antes | Después | Medido el | Responsable |
|---|---|---|---|---|
| `HUM_SECO` | 4095 | | | |
| `HUM_HUMEDO` | 1620 | | | |
| `LUZ_OSCURO_LOG` | 4000 | | | |
| `LUZ_CLARO_LOG` | 30 | | | |
