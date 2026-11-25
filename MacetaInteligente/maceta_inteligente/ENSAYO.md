# Ensayo y presentación

Ensayo: 2 de diciembre de 2026. Congelar código y respaldo: 1 de diciembre. **Presentación: jueves 3 de diciembre de 2026.** Los comandos están en `COMO_CORRER.md`.

## 1. El 1 de diciembre
- [ ] Recalibración terminada, o anotada como pendiente
- [ ] Pruebas del servidor sin fallos
- [ ] Último cambio guardado en git y commit anotado: ____________
- [ ] CSV de la maceta descargados: historial, crecimiento y diario
- [ ] Con el servidor cerrado, copia de `servidor\datos` en una memoria USB propia
- [ ] Copia del proyecto en la misma USB. Contiene `secrets.h`: no la prestes
- [ ] Capturas y un video corto del sistema real funcionando
- [ ] Desde aquí solo se corrigen fallos que impidan presentar

## 2. Qué llevar
- [ ] Maceta ensamblada, con planta; agua y paño
- [ ] PC con cargador; celular con cargador y datos
- [ ] Cable USB de datos, adaptador de corriente y extensión
- [ ] USB de respaldo, regla para las fotos y lámpara si se usará
- [ ] Destornillador y cables de repuesto
- [ ] Adaptador de video para el proyector

## 3. Arranque (empieza 30 min antes)
1. [ ] PC conectado a la corriente, sin suspensión ni actualizaciones
2. [ ] Hotspot encendido, banda de 2,4 GHz. El nombre y la clave deben ser los que ya tiene la maceta
3. [ ] PC conectado al hotspot, con máximo 6 equipos en total
4. [ ] Maceta encendida; IP que muestra el LCD: ____________
5. [ ] Servidor abierto (paso 3 de `COMO_CORRER.md`)
6. [ ] Simuladas encendidas (paso 4 de `COMO_CORRER.md`)
7. [ ] En el PC, `http://127.0.0.1:8000`. Si cambió la IP: Maceta 1 → Conexión → Cambiar dirección
8. [ ] Maceta 1 aparece **Real** y **Conectada**; las demás, **Simulada**
9. [ ] Escalabilidad: 1 real conectada. Las simuladas no cuentan

## 4. Prueba del celular y la foto
1. [ ] En el PC abre el menú ☰ → «Abrir en el celular» y escribe en el celular esa dirección, con `http://`
2. [ ] Entra sin pedir código y sin botones para agregar o borrar macetas
3. [ ] Maceta 1 → Fotos del crecimiento → Tomar foto, con la regla visible
4. [ ] La foto aparece en el celular y en el PC
5. [ ] Fecha y orientación correctas
6. [ ] Comparar dos fotos
7. [ ] Enviar una de prueba a la papelera y restaurarla

| Prueba | Fecha | Celular y navegador | Resultado |
|---|---|---|---|
| Entrada sin código | | | |
| Foto con la cámara | | | |
| Fecha y orientación | | | |

## 5. Guion (unos 8 min)
| Min | Qué mostrar | Qué decir |
|---|---|---|
| 0–1 | Problema y maceta | Ayuda a cuidar una planta con datos de humedad y luz |
| 1–3 | Maceta y LCD | Humedad (YL-69, resistivo) y luz (LDR) son **medidas**; índice y estado son **estimados por reglas**, sin IA |
| 3–4 | Jardín en el PC | Una maceta real; las otras cuatro son **simuladas** para mostrar el crecimiento del sistema |
| 4–5 | Historial y datos técnicos | Adquisición, unidades, calibración y procedencia |
| 5–6 | Apagar una simulada (`1` y Enter) | Se marca sin conexión en unos 30 s y conserva su historial |
| 6–7 | Foto desde el celular y comparación | Altura y hojas se **registran a mano** |
| 7–8 | Escalabilidad, límites y futuro | El hotspot limita a 6 equipos; con el PC, 5 macetas es una capacidad **estimada** |

Para cambiar el estado real: tapar o iluminar la LDR es lo más seguro. No pongas a prueba el encharcamiento frente al público si no quedó validado en `RECALIBRACION.md`.

**Si preguntan:** la humedad es relativa a la calibración; el YL-69 puede corroerse; la LDR no mide lux; casi todas las lecturas hasta el 24-nov son con la sonda fuera de la tierra; los lux y temperatura que aparecen son simulados; la página de la maceta no tiene contraseña y se usa en red privada; el agente de IA es futuro, cuando haya datos reales.

## 6. Plan B
| Falla | Qué hacer |
|---|---|
| La maceta no se conecta | El LCD y las reglas siguen funcionando. Revisa 2,4 GHz, nombre del hotspot e IP. Reinicia una vez |
| La maceta no enciende | Cambia cable y adaptador. Muestra su historial guardado y el video, diciendo que es grabado |
| Un sensor falla | Muéstralo como «dato no fiable»; usa el historial real y las simuladas, identificadas |
| El hotspot no funciona | Reinícialo. El PC sigue con `http://127.0.0.1:8000`, historial y simuladas |
| El celular no abre el PC | Revisa la dirección y la red. Muestra la vista en el PC y sube una foto pasada por cable |
| La cámara no abre | Usa «Subir fotos» con una foto tomada antes |
| El puerto 8000 está ocupado | El servidor ya está abierto: úsalo o cierra la otra ventana |
| El PC falla | Desde el celular abre la página propia de la maceta: `http://IP-de-la-maceta`. Usa capturas y video |
| Todo falla | Video, capturas y explicación del circuito con la maceta en la mano |

## 7. Ensayo
- [ ] Arranque completo desde cero, con el PC recién encendido. Tiempo: ____ min
- [ ] Guion completo dos veces. Tiempos: ____ y ____ min
- [ ] Probar tres fallas: maceta apagada, hotspot apagado y celular sin acceso
- [ ] 30 min encendido sin reinicios ni pérdida de conexión
- [ ] Anotar fallos y corregir solo los que impidan presentar

| Fallo encontrado | Cómo se resolvió |
|---|---|
| | |

## 8. Al terminar
- [ ] Cerrar simuladas (`s`) y servidor (`Ctrl+C`)
- [ ] Copiar otra vez `servidor\datos` y los CSV de la maceta
- [ ] Apagar el hotspot
