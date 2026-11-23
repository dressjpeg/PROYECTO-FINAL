/*
  Maceta inteligente - ESP32 (version con USB, v3)
  Mide humedad de suelo y luz, estima la salud de la planta con reglas
  (sin IA generativa) y la muestra en un LCD 16x2 I2C.

  Conexiones: humedad AO -> D34, luz AO -> D35, LCD SDA -> D21, SCL -> D22.
  El "indice de salud" es una ESTIMACION por software, no una medicion directa.

  Cambios v2:
  - Agua y luz se evaluan por separado: si hay varios problemas a la vez,
    cada uno tiene su propia pantalla (antes la sed tapaba la luz).
  - Pantallas mas lentas (ajustables en T_MENSAJE, T_DATOS y T_SALUD).

  Cambios v3 (16/11/2026):
  - Luz en ESCALA LOGARITMICA (luzPorcentajeLog). La LDR responde de forma
    aproximadamente logaritmica a la luz; con el mapeo lineal la luz de dia,
    aunque fuera sombra o cielo nublado, quedaba siempre cerca de 100 %.
    Se reemplazan LUZ_OSCURO / LUZ_CLARO por LUZ_OSCURO_LOG / LUZ_CLARO_LOG.
    Mediciones de referencia (luz_raw): bombilla ~1650, sombra con luz
    reflejada ~1120, balcon nublado sin sol directo ~130, cielo abierto ~93.
*/
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <math.h>

// ===== Pines =====
const int PIN_HUM = 34;
const int PIN_LUZ = 35;

// ===== Calibracion (lecturas crudas medidas, ADC de 12 bits) =====
// Ambos sensores bajan su valor cuando hay mas agua / mas luz.
const int HUM_SECO   = 4095;   // sonda al aire
const int HUM_HUMEDO = 1620;   // dientes de la sonda en agua

// Luz con escala logaritmica (ver luzPorcentajeLog)
const int LUZ_OSCURO_LOG = 4000;  // casi oscuro = 0 %. No usar 4095 (division entre 0)
const int LUZ_CLARO_LOG  = 30;    // PROVISIONAL: sol directo estimado = 100 %.
                                  // Medir un dia soleado: sensor al sol directo y anotar el luz_raw mas bajo

// ===== Umbrales (en porcentaje) =====
const int UMBRAL_SED       = 30;
const int UMBRAL_EXCESO    = 85;
const int UMBRAL_POCA_LUZ  = 20;
const int UMBRAL_MUCHA_LUZ = 90;
const int UMBRAL_ESTRES    = 70;   // indice de salud por debajo de esto = estresada
const int SALTO_RIEGO      = 15;   // subida de humedad que cuenta como riego

// ===== Tiempo =====
const unsigned long MS_POR_HORA = 3600000UL;  // real. Para probar rapido: 1000UL (1 hora = 1 segundo)
const int HORAS_GRACIA      = 24;
const int PERDIDA_POR_HORA  = 2;
const unsigned long T_MUESTRA   = 1000;       // leer sensores cada 1 s
const unsigned long T_RIEGO     = 10000;      // ventana para detectar riego
const unsigned long T_CONFIRMAR = 5000;       // un cambio debe durar 5 s para mostrarse

// Cuanto dura cada pantalla (en milisegundos)
const unsigned long T_MENSAJE = 15000;   // cada aviso o mensaje de la planta
const unsigned long T_DATOS   = 10000;   // porcentajes de agua y luz
const unsigned long T_SALUD   = 8000;    // salud y horas sin regar

// ===== Personalidad: 0 dramatica, 1 calmada, 2 graciosa =====
const int PERSONALIDAD = 0;

enum { SED, ENCHARCADA, POCA_LUZ, MUCHA_LUZ, FELIZ, ESTRESADA };

// Sin acentos ni enie (el LCD no los muestra) y maximo 16 caracteres
const char* const FRASES[3][6] = {
  { "Me muero de sed!", "Me ahogo! Basta!", "Esta muy oscuro!", "Me quemo al sol!", "Soy muy feliz!!", "Me siento mal..." },
  { "Riego, por favor", "Mucha agua hoy",   "Busco mas luz",    "Mucho sol hoy",    "Todo en orden",   "Necesito cuidado" },
  { "Un traguito pls",  "Piscina privada!", "Prende la luz!",   "Modo bronceado!",  "Vida de planta!", "Dia dificil..." }
};

LiquidCrystal_I2C *lcd = nullptr;

int hRaw = 0, lRaw = 0, hPct = 0, lPct = 0, indice = 100;
int estadoActual = FELIZ;            // estado principal (para el monitor serie y el dashboard)
int alertas[3];                      // avisos activos (valores del enum)
int nAlertas = 1;
unsigned long tUltimoRiego = 0, tUltimaMuestra = 0, tRef = 0, tPantalla = 0;
int hRef = 0;
int pantalla = 0;
char cacheLinea[2][17];

// Confirmacion de cambios: 0 = agua, 1 = luz, 2 = estres
int dbActual[3] = {0, 0, 0};
int dbCandidato[3] = {0, 0, 0};
unsigned long dbTiempo[3] = {0, 0, 0};

// ---------- Lectura ----------
int leerPromedio(int pin) {
  long suma = 0;
  for (int i = 0; i < 10; i++) {
    suma += analogRead(pin);
    delay(2);
  }
  return suma / 10;
}

int aPorcentaje(int raw, int valorCero, int valorCien) {
  return constrain(map(raw, valorCero, valorCien, 0, 100), 0, 100);
}

// Luz en escala logaritmica.
// El modulo es un divisor: la LDR va a GND y una R fija a 3V3, asi que
// raw / (4095 - raw) es proporcional a la resistencia de la LDR (la R fija
// se cancela). El porcentaje se calcula sobre el logaritmo de esa resistencia.
float rRelLuz(int raw) {
  return (float)raw / (4095.0f - raw);
}

int luzPorcentajeLog(int raw) {
  raw = constrain(raw, LUZ_CLARO_LOG, LUZ_OSCURO_LOG);
  float total = logf(rRelLuz(LUZ_OSCURO_LOG) / rRelLuz(LUZ_CLARO_LOG));
  float pct   = 100.0f * logf(rRelLuz(LUZ_OSCURO_LOG) / rRelLuz(raw)) / total;
  return constrain((int)roundf(pct), 0, 100);
}

// ---------- Indice de salud estimado ----------
int puntajeHum(int h) {
  if (h < 40) return h * 100 / 40;
  if (h > 75) return (100 - h) * 100 / 25;
  return 100;
}

int puntajeLuz(int l) {
  if (l < 30) return l * 100 / 30;
  if (l > 80) return (100 - l) * 100 / 20;
  return 100;
}

int puntajeTiempo(unsigned long horas) {
  if (horas <= (unsigned long)HORAS_GRACIA) return 100;
  long p = 100 - (long)(horas - HORAS_GRACIA) * PERDIDA_POR_HORA;
  return p < 0 ? 0 : (int)p;
}

// humedad 50 %, luz 30 %, tiempo desde el riego 20 %
int calcularIndice(int h, int l, unsigned long horas) {
  return (50 * puntajeHum(h) + 30 * puntajeLuz(l) + 20 * puntajeTiempo(horas)) / 100;
}

// ---------- Reglas ----------
int categoriaAgua(int h) {   // 0 bien, 1 seca, 2 encharcada
  if (h < UMBRAL_SED) return 1;
  if (h > UMBRAL_EXCESO) return 2;
  return 0;
}

int categoriaLuz(int l) {    // 0 bien, 1 poca, 2 mucha
  if (l < UMBRAL_POCA_LUZ) return 1;
  if (l > UMBRAL_MUCHA_LUZ) return 2;
  return 0;
}

// Un valor nuevo solo se acepta si se mantiene T_CONFIRMAR ms
int confirmar(int i, int nuevo) {
  if (nuevo == dbActual[i]) { dbCandidato[i] = nuevo; return dbActual[i]; }
  if (nuevo != dbCandidato[i]) { dbCandidato[i] = nuevo; dbTiempo[i] = millis(); return dbActual[i]; }
  if (millis() - dbTiempo[i] >= T_CONFIRMAR) dbActual[i] = nuevo;
  return dbActual[i];
}

// Junta los avisos activos. El de estres solo aparece si no hay otro.
void construirAlertas(int agua, int luz, int estres) {
  nAlertas = 0;
  if (agua == 1) alertas[nAlertas++] = SED;
  if (agua == 2) alertas[nAlertas++] = ENCHARCADA;
  if (luz == 1) alertas[nAlertas++] = POCA_LUZ;
  if (luz == 2) alertas[nAlertas++] = MUCHA_LUZ;
  if (nAlertas == 0) alertas[nAlertas++] = estres ? ESTRESADA : FELIZ;
  estadoActual = alertas[0];
}

const char* estadoAgua(int h) {
  if (h < UMBRAL_SED) return "SECA";
  if (h > UMBRAL_EXCESO) return "MUCHA";
  return "OK";
}

const char* estadoLuz(int l) {
  if (l < UMBRAL_POCA_LUZ) return "BAJA";
  if (l > UMBRAL_MUCHA_LUZ) return "ALTA";
  return "OK";
}

// ---------- LCD ----------
void linea(int fila, const char* texto) {
  char buf[17];
  snprintf(buf, sizeof(buf), "%-16s", texto);
  if (strcmp(buf, cacheLinea[fila]) == 0) return;
  strcpy(cacheLinea[fila], buf);
  if (lcd) {
    lcd->setCursor(0, fila);
    lcd->print(buf);
  }
}

// Linea de arriba: que le falta o le sobra, con su porcentaje
void armarLinea0(int estado, char* buf) {
  switch (estado) {
    case SED:        snprintf(buf, 17, "Falta agua: %d%%", hPct); break;
    case ENCHARCADA: snprintf(buf, 17, "Exceso agua:%d%%", hPct); break;
    case POCA_LUZ:   snprintf(buf, 17, "Falta luz: %d%%", lPct); break;
    case MUCHA_LUZ:  snprintf(buf, 17, "Exceso luz: %d%%", lPct); break;
    default:         snprintf(buf, 17, "Agua%d%% Luz%d%%", hPct, lPct); break;
  }
}

// Pantallas: un mensaje por cada aviso activo, luego datos, luego salud
void dibujar() {
  unsigned long ahora = millis();
  int total = nAlertas + 2;
  if (pantalla >= total) pantalla = 0;

  unsigned long duracion = T_SALUD;
  if (pantalla < nAlertas) duracion = T_MENSAJE;
  else if (pantalla == nAlertas) duracion = T_DATOS;

  if (ahora - tPantalla >= duracion) {
    pantalla = (pantalla + 1) % total;
    tPantalla = ahora;
  }

  char b[17];
  unsigned long horas = (ahora - tUltimoRiego) / MS_POR_HORA;
  if (horas > 999) horas = 999;

  if (pantalla < nAlertas) {
    armarLinea0(alertas[pantalla], b);
    linea(0, b);
    linea(1, FRASES[PERSONALIDAD][alertas[pantalla]]);
  } else if (pantalla == nAlertas) {
    snprintf(b, sizeof(b), "Agua:%3d%% %s", hPct, estadoAgua(hPct));
    linea(0, b);
    snprintf(b, sizeof(b), "Luz :%3d%% %s", lPct, estadoLuz(lPct));
    linea(1, b);
  } else {
    snprintf(b, sizeof(b), "Salud: %d%%", indice);
    linea(0, b);
    snprintf(b, sizeof(b), "Sin regar: %luh", horas);
    linea(1, b);
  }
}

// ---------- Arranque ----------
void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  analogReadResolution(12);

  uint8_t dir = 0;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0 && (a == 0x27 || a == 0x3F)) dir = a;
  }
  if (dir) {
    lcd = new LiquidCrystal_I2C(dir, 16, 2);
    lcd->init();
    lcd->backlight();
  } else {
    Serial.println("No encontre el LCD: revisa 5V, GND, SDA y SCL");
  }

  linea(0, "Maceta lista");
  linea(1, "Leyendo...");

  alertas[0] = FELIZ;
  hRaw = leerPromedio(PIN_HUM);
  hRef = aPorcentaje(hRaw, HUM_SECO, HUM_HUMEDO);
  tUltimoRiego = millis();   // al encender se asume planta recien regada
  tRef = millis();
  tPantalla = millis();
  Serial.println("hum_raw,luz_raw,hum_pct,luz_pct,indice,estado");
}

void loop() {
  unsigned long ahora = millis();
  if (ahora - tUltimaMuestra < T_MUESTRA) return;
  tUltimaMuestra = ahora;

  hRaw = leerPromedio(PIN_HUM);
  lRaw = leerPromedio(PIN_LUZ);
  hPct = aPorcentaje(hRaw, HUM_SECO, HUM_HUMEDO);
  lPct = luzPorcentajeLog(lRaw);   // v3: escala logaritmica

  // Riego = la humedad sube SALTO_RIEGO puntos o mas dentro de la ventana
  if (ahora - tRef >= T_RIEGO) {
    if (hPct - hRef >= SALTO_RIEGO) tUltimoRiego = ahora;
    hRef = hPct;
    tRef = ahora;
  }

  unsigned long horas = (ahora - tUltimoRiego) / MS_POR_HORA;
  indice = calcularIndice(hPct, lPct, horas);

  int agua = confirmar(0, categoriaAgua(hPct));
  int luz = confirmar(1, categoriaLuz(lPct));
  int estres = confirmar(2, indice < UMBRAL_ESTRES ? 1 : 0);
  construirAlertas(agua, luz, estres);

  Serial.printf("%d,%d,%d,%d,%d,%d\n", hRaw, lRaw, hPct, lPct, indice, estadoActual);
  dibujar();
}