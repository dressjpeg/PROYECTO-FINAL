/*
  Dashboard web de la maceta inteligente (pestaña aparte del sketch).
  Solo LEE las variables del firmware v3. Única excepción: POST /api/riego
  reinicia tUltimoRiego, igual que un riego detectado.

  DASH_WIFI_ON 0 -> no se enlaza WiFi ni LittleFS y queda como la v3.
*/
#define DASH_WIFI_ON 1

#if !DASH_WIFI_ON
void dashboardIniciar() {}
void dashboardAtender() {}
void dashboardRegistrar() {}
#else

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <LittleFS.h>
#include <esp_timer.h>
#include <stdarg.h>
#include <time.h>
#include <sys/select.h>
#include "PaginaWeb.h"
#if __has_include("secrets.h")
#include "secrets.h"
#else
#error "Falta secrets.h: copia secrets.example.h como secrets.h y escribe tu red"
#endif

// ===== Ajustes =====
const unsigned long DASH_T_ESPERA_WIFI = 10000;   // máximo en setup
const unsigned long DASH_T_MOSTRAR_IP  = 5000;
// Menos potencia = menos picos de corriente (la luz del LCD titila con USB débil).
// Si la maceta queda lejos del router: WIFI_POWER_15dBm o WIFI_POWER_19_5dBm
const wifi_power_t DASH_POTENCIA_WIFI = WIFI_POWER_8_5dBm;
const unsigned long DASH_T_REINTENTO   = 30000;
const unsigned long DASH_T_HISTORIAL   = 300000;  // una lectura cada 5 min
const int DASH_REG_SEGMENTO = 288;                // 1 día por archivo
const int DASH_SEGMENTOS    = 8;                  // 7 días completos + el actual
const uint32_t DASH_MIN_ALERTA_AGUA = 10;         // SED y ENCHARCADA (minutos)
const uint32_t DASH_MIN_ALERTA_OTRAS = 30;        // luz y ESTRESADA (minutos)
const int DASH_MAX_RESUELTAS = 10;
const int DASH_MAX_CRECIMIENTO = 500;
const int DASH_MAX_DIAS = 400;
const unsigned long DASH_T_PARCIAL = 3600000UL;   // respaldo del día cada hora
const unsigned long DASH_T_MISMO_RIEGO = 300000;  // riegos más juntos cuentan como uno
const time_t DASH_EPOCH_MIN = 1735689600;         // antes de 2025 = no hay hora real

const char* const EST_CLAVE[6] = { "SED", "ENCHARCADA", "POCA_LUZ", "MUCHA_LUZ", "FELIZ", "ESTRESADA" };
const char* const EST_TEXTO[6] = { "Sed", "Encharcada", "Poca luz", "Mucha luz", "Feliz", "Estresada" };

// ===== Servidor =====
// Los navegadores abren conexiones de reserva sin enviar nada y WebServer las
// espera 5 s, bloqueando a las demás. Aquí se sueltan a los 800 ms.
class ServidorMaceta : public WebServer {
public:
  ServidorMaceta() : WebServer(80) {}
  void soltarInactivo() {
    if (_currentStatus == HC_WAIT_READ && !_currentClient.available() && millis() - _statusChange > 800)
      _statusChange = millis() - HTTP_MAX_DATA_WAIT - 1;
  }
};
ServidorMaceta servidor;

bool dashConectado = false, dashMdns = false, dashFs = false, dashHayMuestra = false;
unsigned long dashTReintento = 0;
uint32_t dashFsUsado = 0, dashFsTotal = 0;
uint16_t dashArranque = 0;

uint32_t uptimeS() { return (uint32_t)(esp_timer_get_time() / 1000000LL); }
bool horaReal() { return time(nullptr) > DASH_EPOCH_MIN; }
unsigned long horasSinRegar() { return (millis() - tUltimoRiego) / MS_POR_HORA; }
bool hayAviso(int e) {
  for (int i = 0; i < nAlertas; i++) if (alertas[i] == e) return true;
  return false;
}
void medirFs() { if (dashFs) { dashFsUsado = LittleFS.usedBytes(); dashFsTotal = LittleFS.totalBytes(); } }

// ----- Respuestas por partes con un buffer fijo -----
char salBuf[1024];
size_t salN = 0;
bool salRota = false;

// Espera como mucho 1 s a que el celular reciba; si no, corta la respuesta
bool clienteListo() {
  int s = servidor.client().fd();
  if (s < 0) return false;
  fd_set w; FD_ZERO(&w); FD_SET(s, &w);
  struct timeval tv = { 1, 0 };
  return select(s + 1, nullptr, &w, nullptr, &tv) > 0 && FD_ISSET(s, &w);
}
void salEnviar() {
  if (salN && !salRota) {
    if (clienteListo()) servidor.sendContent(salBuf, salN);
    else { salRota = true; servidor.client().stop(); }
  }
  salN = 0;
}
void sal(const char* f, ...) {
  if (salRota) return;
  char t[320];
  va_list a; va_start(a, f);
  int n = vsnprintf(t, sizeof(t), f, a);
  va_end(a);
  if (n <= 0) return;
  if (n >= (int)sizeof(t)) n = sizeof(t) - 1;
  if (salN + n > sizeof(salBuf)) salEnviar();
  memcpy(salBuf + salN, t, n);
  salN += n;
}
void salTexto(const char* s) {   // cadena JSON con escape
  sal("\"");
  for (; *s; s++) {
    unsigned char c = *s;
    if (c == '"' || c == '\\') sal("\\%c", c);
    else if (c < 32 || c == '<') sal("\\u%04x", c);
    else sal("%c", c);
  }
  sal("\"");
}
void respIni(const char* tipo) {
  salN = 0; salRota = false;
  servidor.sendHeader("Cache-Control", "no-store");
  servidor.setContentLength(CONTENT_LENGTH_UNKNOWN);
  servidor.send(200, tipo, "");
}
void respJson() { respIni("application/json; charset=utf-8"); }
void respFin() { salEnviar(); if (!salRota) servidor.sendContent("", 0); }
void respError(int codigo, const char* msg) {
  char b[128];
  snprintf(b, sizeof(b), "{\"ok\":false,\"error\":\"%s\"}", msg);
  servidor.send(codigo, "application/json; charset=utf-8", b);
}
void respOk() { servidor.send(200, "application/json", "{\"ok\":true}"); }
// Cabecera propia: impide que otra web abierta en el celular modifique datos
bool permitido() {
  if (servidor.header("X-Maceta") == "1") return true;
  respError(403, "Falta la cabecera X-Maceta");
  return false;
}
void respCsv(const char* nombre) {
  char b[64];
  snprintf(b, sizeof(b), "attachment; filename=\"%s\"", nombre);
  servidor.sendHeader("Content-Disposition", b);
  respIni("text/csv; charset=utf-8");
  sal("\xEF\xBB\xBF");   // BOM: Excel reconoce los acentos
}

// ===== Historial: segmentos binarios que solo crecen al final =====
struct __attribute__((packed)) RegHist {
  uint32_t t;          // epoch, o uptime si real = 0
  uint16_t arranque;
  uint16_t hRaw, lRaw;
  uint8_t real, estado, hPct, lPct, indice, suma;
  uint8_t calcular() const {
    uint8_t s = 0x5A;
    for (size_t i = 0; i < sizeof(RegHist) - 1; i++) s = s * 31 + ((const uint8_t*)this)[i];
    return s;
  }
};
uint32_t histIni = 0, histFin = 0;   // números de segmento
unsigned long histT = 0;

void histRuta(char* b, size_t n, uint32_t s) { snprintf(b, n, "/h/%lu.bin", (unsigned long)s); }
int histCuenta(uint32_t s) {
  char r[24]; histRuta(r, sizeof(r), s);
  if (!LittleFS.exists(r)) return 0;
  File f = LittleFS.open(r, "r");
  int n = f ? f.size() / sizeof(RegHist) : 0;
  f.close();
  return n;
}
void histIniciar() {
  LittleFS.mkdir("/h");
  bool alguno = false;
  File d = LittleFS.open("/h");
  if (!d) return;
  for (File f = d.openNextFile(); f; f = d.openNextFile()) {
    uint32_t s = strtoul(f.name(), nullptr, 10);
    if (!alguno || s < histIni) histIni = s;
    if (!alguno || s > histFin) histFin = s;
    alguno = true;
  }
  histT = millis();
}
void histGuardar() {
  if (!dashFs || millis() - histT < DASH_T_HISTORIAL) return;
  histT = millis();
  if (histCuenta(histFin) >= DASH_REG_SEGMENTO) histFin++;
  char r[24];
  while (histFin - histIni >= (uint32_t)DASH_SEGMENTOS) {
    histRuta(r, sizeof(r), histIni++);
    if (LittleFS.exists(r)) LittleFS.remove(r);
  }
  RegHist g;
  g.real = horaReal();
  g.t = g.real ? (uint32_t)time(nullptr) : uptimeS();
  g.arranque = dashArranque;
  g.hRaw = hRaw; g.lRaw = lRaw; g.hPct = hPct; g.lPct = lPct;
  g.indice = indice; g.estado = estadoActual;
  g.suma = g.calcular();
  histRuta(r, sizeof(r), histFin);
  File f = LittleFS.open(r, "a");
  if (!f || f.write((uint8_t*)&g, sizeof(g)) != sizeof(g)) Serial.println("# Error guardando historial");
  f.close();
  medirFs();
}
void fechaHora(uint32_t t, char* b, size_t n) {
  time_t x = t; struct tm m;
  localtime_r(&x, &m);
  strftime(b, n, "%Y-%m-%d %H:%M:%S", &m);
}
// maxReg: últimos N registros; rango en s (0 = todos)
void histEnviar(int maxReg, uint32_t rango, bool csv) {
  int total = 0;
  for (uint32_t s = histIni; s <= histFin; s++) total += histCuenta(s);
  int saltar = (maxReg && total > maxReg) ? total - maxReg : 0;
  bool hr = horaReal(), primero = true;
  uint32_t ahora = hr ? (uint32_t)time(nullptr) : 0, up = uptimeS();
  RegHist b[16];
  for (uint32_t s = histIni; s <= histFin && !salRota; s++) {
    int n = histCuenta(s);
    if (saltar >= n) { saltar -= n; continue; }
    char r[24]; histRuta(r, sizeof(r), s);
    File f = LittleFS.open(r, "r");
    if (!f) { saltar = 0; continue; }
    f.seek(saltar * sizeof(RegHist));
    saltar = 0;
    int leidos;
    while (!salRota && (leidos = f.read((uint8_t*)b, sizeof(b)) / (int)sizeof(RegHist)) > 0) {
      for (int i = 0; i < leidos; i++) {
        RegHist& g = b[i];
        if (g.suma != g.calcular() || g.estado > 5) continue;
        // 0 sin hora, 1 hora real, 2 corregida con NTP del mismo arranque
        int fuente = g.real;
        uint32_t t = g.t;
        if (!fuente && g.arranque == dashArranque) {
          if (hr) { t = ahora - (up - g.t); fuente = 2; }
          else if (rango && up - g.t > rango) continue;
        }
        if (fuente && hr && rango && ahora > t && ahora - t > rango) continue;
        if (csv) {
          char h[24] = "";
          if (fuente) fechaHora(t, h, sizeof(h));
          sal("%s;%s;%lu;%u;%u;%u;%u;%u;%u;%s\r\n", h, fuente == 1 ? "real" : fuente == 2 ? "corregida" : "sin hora (uptime)",
              (unsigned long)t, g.arranque, g.hRaw, g.lRaw, g.hPct, g.lPct, g.indice, EST_CLAVE[g.estado]);
        } else {
          sal("%s[%lu,%d,%u,%u,%u,%u,%u,%u,%u]", primero ? "" : ",", (unsigned long)t, fuente, g.hPct, g.lPct,
              g.indice, g.estado, g.hRaw, g.lRaw, g.arranque);
        }
        primero = false;
      }
    }
    f.close();
  }
}
void apiHistorial() {
  if (!dashFs) return respError(503, "LittleFS no disponible");
  String r = servidor.arg("rango");
  int n; uint32_t s;
  if (r == "" || r == "1h") { n = 13; s = 3600; }
  else if (r == "24h") { n = 289; s = 86400; }
  else if (r == "7d") { n = 2017; s = 604800; }
  else return respError(400, "rango debe ser 1h, 24h o 7d");
  respJson();
  sal("{\"hora_real\":%s,\"ahora\":%lu,\"uptime_s\":%lu,\"arranque\":%u,", horaReal() ? "true" : "false",
      horaReal() ? (unsigned long)time(nullptr) : 0UL, (unsigned long)uptimeS(), dashArranque);
  sal("\"campos\":[\"t\",\"hora\",\"hum_pct\",\"luz_pct\",\"indice\",\"estado\",\"hum_raw\",\"luz_raw\",\"arranque\"],\"datos\":[");
  histEnviar(n, s, false);
  sal("]}");
  respFin();
}
void apiHistorialCsv() {
  if (!dashFs) return respError(503, "LittleFS no disponible");
  respCsv("historial.csv");
  sal("fecha_hora;hora;t;arranque;hum_raw;luz_raw;hum_pct;luz_pct;indice_estimado;estado\r\n");
  histEnviar(0, 0, true);
  respFin();
}

// ===== Alertas sostenidas =====
struct Alerta { bool activa, sostenida; uint32_t desde; };   // desde = uptime
Alerta alertaEst[6];
struct Resuelta { uint32_t tipo, inicio, fin, duracion; };   // epoch, 0 = sin hora
Resuelta resueltas[DASH_MAX_RESUELTAS];
int nResueltas = 0;

uint32_t segundosAlerta(int e) {
  return 60 * ((e == SED || e == ENCHARCADA) ? DASH_MIN_ALERTA_AGUA : DASH_MIN_ALERTA_OTRAS);
}
void alertasIniciar() {
  if (!dashFs || !LittleFS.exists("/resueltas.bin")) return;
  File f = LittleFS.open("/resueltas.bin", "r");
  while (nResueltas < DASH_MAX_RESUELTAS && f.read((uint8_t*)&resueltas[nResueltas], sizeof(Resuelta)) == sizeof(Resuelta))
    if (resueltas[nResueltas].tipo <= ESTRESADA) nResueltas++;
  f.close();
}
void alertaResuelta(int e, uint32_t dur) {
  if (nResueltas < DASH_MAX_RESUELTAS) nResueltas++;
  for (int i = nResueltas - 1; i > 0; i--) resueltas[i] = resueltas[i - 1];
  uint32_t ahora = horaReal() ? (uint32_t)time(nullptr) : 0;
  resueltas[0] = { (uint32_t)e, ahora ? ahora - dur : 0, ahora, dur };
  if (!dashFs) return;
  File f = LittleFS.open("/resueltas.bin", "w");
  if (f) f.write((uint8_t*)resueltas, nResueltas * sizeof(Resuelta));
  f.close();
}
void alertasRegistrar() {
  uint32_t up = uptimeS();
  for (int e = 0; e < 6; e++) {
    if (e == FELIZ) continue;
    Alerta& a = alertaEst[e];
    bool hay = hayAviso(e);
    if (hay && !a.activa) a = { true, false, up };
    if (hay && up - a.desde >= segundosAlerta(e)) a.sostenida = true;
    if (!hay && a.activa) {
      if (a.sostenida) alertaResuelta(e, up - a.desde);
      a.activa = a.sostenida = false;
    }
  }
}

// ===== Lectura de líneas (File global: el IDE genera prototipos antes de los includes) =====
File gF;
bool leerLinea(char* b, size_t n) {
  size_t i = 0; int c; bool algo = false;
  while ((c = gF.read()) >= 0) {
    algo = true;
    if (c == '\n') break;
    if (c != '\r' && i < n - 1) b[i++] = c;
  }
  b[i] = 0;
  return algo;
}
int contarLineas(const char* ruta) {
  if (!LittleFS.exists(ruta)) return 0;
  char b[320]; int n = 0;
  gF = LittleFS.open(ruta, "r");
  while (leerLinea(b, sizeof(b))) if (b[0]) n++;
  gF.close();
  return n;
}

// ===== Resumen diario =====
uint32_t fechaHoy() {
  time_t x = time(nullptr); struct tm m;
  localtime_r(&x, &m);
  return (m.tm_year + 1900) * 10000UL + (m.tm_mon + 1) * 100 + m.tm_mday;
}
struct Dia {
  uint32_t magia, fecha;   // fecha AAAAMMDD, 0 = sin hora real
  uint32_t n, ms, sumH, sumL, sumI, riegos;
  uint32_t msEst[6];
  uint8_t hMin, hMax, lMin, lMax;
  void limpiar() { memset(this, 0, sizeof(*this)); magia = 0x4D414331; hMin = lMin = 255; }
  void agregar(uint32_t dt) {
    n++; ms += dt; sumH += hPct; sumL += lPct; sumI += indice;
    if (hPct < hMin) hMin = hPct;
    if (hPct > hMax) hMax = hPct;
    if (lPct < lMin) lMin = lPct;
    if (lPct > lMax) lMax = lPct;
    for (int e = 0; e < 6; e++) if (e != FELIZ && hayAviso(e)) msEst[e] += dt;
  }
  void fusionar(const Dia& o) {
    n += o.n; ms += o.ms; sumH += o.sumH; sumL += o.sumL; sumI += o.sumI; riegos += o.riegos;
    for (int e = 0; e < 6; e++) msEst[e] += o.msEst[e];
    if (o.hMin < hMin) hMin = o.hMin;
    if (o.hMax > hMax) hMax = o.hMax;
    if (o.lMin < lMin) lMin = o.lMin;
    if (o.lMax > lMax) lMax = o.lMax;
  }
  // fecha,hprom,hmin,hmax,lprom,lmin,lmax,iprom,riegos,5 x minutos,muestras
  void fila(char* b, size_t tam) const {
    char f[16] = "sin_hora";
    if (fecha) snprintf(f, sizeof(f), "%04lu-%02lu-%02lu", (unsigned long)(fecha / 10000), (unsigned long)(fecha / 100 % 100), (unsigned long)(fecha % 100));
    snprintf(b, tam, "%s,%.1f,%u,%u,%.1f,%u,%u,%.1f,%lu,%lu,%lu,%lu,%lu,%lu,%lu", f,
             (float)sumH / n, hMin, hMax, (float)sumL / n, lMin, lMax, (float)sumI / n, (unsigned long)riegos,
             (unsigned long)(msEst[SED] / 60000), (unsigned long)(msEst[ENCHARCADA] / 60000), (unsigned long)(msEst[POCA_LUZ] / 60000),
             (unsigned long)(msEst[MUCHA_LUZ] / 60000), (unsigned long)(msEst[ESTRESADA] / 60000), (unsigned long)n);
  }
  bool cargar(const char* ruta) {
    limpiar();
    if (!LittleFS.exists(ruta)) return false;
    File f = LittleFS.open(ruta, "r");
    Dia t;
    bool ok = f && f.read((uint8_t*)&t, sizeof(t)) == sizeof(t) && t.magia == magia && t.n > 0;
    f.close();
    if (ok) *this = t;
    return ok;
  }
  void guardar(const char* ruta) const {
    File f = LittleFS.open(ruta, "w");
    if (!f || f.write((const uint8_t*)this, sizeof(*this)) != sizeof(*this)) Serial.println("# Error guardando parcial");
    f.close();
  }
};
// diaAct: lo que se acumula. diaPrev: parcial con fecha de antes del reinicio.
// diaSh: parcial sin hora real de antes del reinicio.
Dia diaAct, diaPrev, diaSh;
const char* const R_DIARIO = "/diario.csv";
const char* const R_PARCIAL = "/parcial.bin";
const char* const R_PARCIAL_SH = "/parcial_sh.bin";
unsigned long diaTMuestra = 0, diaTParcial = 0, diaRiegoVisto = 0, diaRiegoContado = 0;
bool diaRiegoIni = false, diaHuboRiego = false;

void borrarSi(const char* r) { if (LittleFS.exists(r)) LittleFS.remove(r); }

// Copia el archivo saltando las primeras `saltar` líneas o la que tenga el id dado (-1 = ninguno)
bool copiarSin(const char* ruta, int saltar, long id) {
  char b[320]; bool ok = true;
  gF = LittleFS.open(ruta, "r");
  File o = LittleFS.open("/tmp.csv", "w");
  if (!gF || !o) ok = false;
  while (ok && leerLinea(b, sizeof(b))) {
    if (saltar > 0) { saltar--; continue; }
    if (!b[0] || (id >= 0 && atol(b) == id)) continue;
    size_t n = strlen(b);
    if (o.write((uint8_t*)b, n) != n || o.write('\n') != 1) ok = false;
  }
  gF.close(); o.close();
  if (ok) ok = LittleFS.rename("/tmp.csv", ruta);
  else borrarSi("/tmp.csv");
  return ok;
}
void diaEscribir(const struct Dia* d) {
  if (!d->n) return;
  char b[160]; d->fila(b, sizeof(b));
  File f = LittleFS.open(R_DIARIO, "a");
  if (!f || f.println(b) == 0) Serial.println("# Error guardando diario");
  f.close();
  int n = contarLineas(R_DIARIO);
  if (n > DASH_MAX_DIAS) copiarSin(R_DIARIO, n - DASH_MAX_DIAS, -1);
  medirFs();
}
void diaGuardarParcial() { diaAct.guardar(diaAct.fecha ? R_PARCIAL : R_PARCIAL_SH); }
void diaIniciar() {
  diaAct.limpiar(); diaPrev.limpiar(); diaSh.limpiar();
  if (!dashFs) return;
  diaPrev.cargar(R_PARCIAL);
  diaSh.cargar(R_PARCIAL_SH);
  diaTParcial = millis();
}
void diaRegistrar() {
  unsigned long m = millis();
  // Riego detectado = el firmware cambió tUltimoRiego
  if (!diaRiegoIni) { diaRiegoIni = true; diaRiegoVisto = tUltimoRiego; diaTMuestra = m; }
  if (tUltimoRiego != diaRiegoVisto) {
    diaRiegoVisto = tUltimoRiego;
    if (!diaHuboRiego || m - diaRiegoContado > DASH_T_MISMO_RIEGO) diaAct.riegos++;
    diaHuboRiego = true; diaRiegoContado = m;
  }
  diaAct.agregar(m - diaTMuestra);
  diaTMuestra = m;
  if (!dashFs) return;

  if (horaReal()) {
    uint32_t hoy = fechaHoy();
    if (!diaAct.fecha) {                       // acaba de llegar la hora
      if (diaSh.n) { diaEscribir(&diaSh); diaSh.limpiar(); }
      if (diaAct.ms > 3600000UL) { diaEscribir(&diaAct); diaAct.limpiar(); }
      diaAct.fecha = hoy;
      if (diaPrev.n) {
        if (diaPrev.fecha == hoy) diaAct.fusionar(diaPrev);
        else diaEscribir(&diaPrev);
        diaPrev.limpiar();
      }
      diaGuardarParcial();
      borrarSi(R_PARCIAL_SH);
    } else if (hoy > diaAct.fecha) {           // cambio de día
      diaEscribir(&diaAct);
      borrarSi(R_PARCIAL);
      diaAct.limpiar();
      diaAct.fecha = hoy;
    }
  } else if (diaAct.ms + diaSh.ms >= 86400000UL) {  // 24 h sin hora real
    diaAct.fusionar(diaSh); diaSh.limpiar();
    diaEscribir(&diaAct);
    borrarSi(R_PARCIAL_SH);
    diaAct.limpiar();
  }
  if (m - diaTParcial >= DASH_T_PARCIAL) {
    diaTParcial = m;
    if (!diaAct.n) return;
    if (!diaAct.fecha && diaSh.n) { diaAct.fusionar(diaSh); diaSh.limpiar(); }
    diaGuardarParcial();
    medirFs();
  }
}
void filaJson(char* b) {   // "AAAA-MM-DD",resto
  char* c = strchr(b, ',');
  if (!c) return;
  *c = 0;
  sal("[\"%s\",%s]", b, c + 1);
}
void apiDiario() {
  if (!dashFs) return respError(503, "LittleFS no disponible");
  String a = servidor.arg("dias");
  int dias = a == "" ? 30 : a.toInt();
  if (dias != 30 && dias != 90 && dias != 365) return respError(400, "dias debe ser 30, 90 o 365");
  int saltar = contarLineas(R_DIARIO) - dias;
  respJson();
  sal("{\"campos\":[\"fecha\",\"hum_prom\",\"hum_min\",\"hum_max\",\"luz_prom\",\"luz_min\",\"luz_max\",\"indice_prom\",\"riegos\",");
  sal("\"min_sed\",\"min_encharcada\",\"min_poca_luz\",\"min_mucha_luz\",\"min_estresada\",\"muestras\"],\"dias\":[");
  char b[320]; bool primero = true;
  if (LittleFS.exists(R_DIARIO)) {
    gF = LittleFS.open(R_DIARIO, "r");
    while (!salRota && leerLinea(b, sizeof(b))) {
      if (saltar-- > 0 || !b[0]) continue;
      if (!primero) sal(",");
      primero = false;
      filaJson(b);
    }
    gF.close();
  }
  sal("],\"hoy_parcial\":");
  if (diaAct.n) { diaAct.fila(b, sizeof(b)); filaJson(b); } else sal("null");
  sal("}");
  respFin();
}
void apiDiarioCsv() {
  if (!dashFs) return respError(503, "LittleFS no disponible");
  respCsv("diario.csv");
  sal("fecha;hum_prom;hum_min;hum_max;luz_prom;luz_min;luz_max;indice_prom_estimado;riegos;min_sed;min_encharcada;min_poca_luz;min_mucha_luz;min_estresada;muestras\r\n");
  if (LittleFS.exists(R_DIARIO)) {
    char b[320];
    gF = LittleFS.open(R_DIARIO, "r");
    while (!salRota && leerLinea(b, sizeof(b))) {
      for (char* p = b; *p; p++) *p = *p == ',' ? ';' : *p == '.' ? ',' : *p;
      sal("%s\r\n", b);
    }
    gF.close();
  }
  respFin();
}

// ===== Crecimiento (registrado a mano): id,fecha,altura,hojas,nota =====
const char* const R_CREC = "/crecimiento.csv";

bool fechaValida(const char* s) {
  if (strlen(s) != 10 || s[4] != '-' || s[7] != '-') return false;
  for (int i = 0; i < 10; i++) if (i != 4 && i != 7 && !isDigit(s[i])) return false;
  int a = atoi(s), m = atoi(s + 5), d = atoi(s + 8);
  const int dm[12] = { 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };
  if (a < 2020 || a > 2099 || m < 1 || m > 12 || d < 1) return false;
  return d <= dm[m - 1] + (m == 2 && a % 4 == 0);
}
// Separa la línea en sus 5 campos (la nota es el último y puede llevar comas)
bool crecPartes(char* b, char** p) {
  for (int i = 0; i < 4; i++) {
    p[i] = b;
    b = strchr(b, ',');
    if (!b) return false;
    *b++ = 0;
  }
  p[4] = b;
  return true;
}
void apiCrecListar() {
  if (!dashFs) return respError(503, "LittleFS no disponible");
  respJson();
  sal("{\"max\":%d,\"registros\":[", DASH_MAX_CRECIMIENTO);
  if (LittleFS.exists(R_CREC)) {
    char b[320]; char* p[5]; bool primero = true;
    gF = LittleFS.open(R_CREC, "r");
    while (!salRota && leerLinea(b, sizeof(b))) {
      if (!crecPartes(b, p)) continue;
      sal("%s{\"id\":%ld,\"fecha\":\"%s\",\"altura\":%s,\"hojas\":%s,\"nota\":", primero ? "" : ",", atol(p[0]), p[1], p[2], p[3]);
      salTexto(p[4]);
      sal("}");
      primero = false;
    }
    gF.close();
  }
  sal("]}");
  respFin();
}
void apiCrecGuardar() {
  if (!permitido()) return;
  if (!dashFs) return respError(503, "LittleFS no disponible");
  String fecha = servidor.arg("fecha"), alt = servidor.arg("altura"), hoj = servidor.arg("hojas"), nota = servidor.arg("nota");
  fecha.trim(); alt.trim(); hoj.trim(); nota.trim();
  if (!fechaValida(fecha.c_str())) return respError(400, "Fecha no válida");
  alt.replace(',', '.');
  // Solo dígitos y punto: descarta "nan", "inf", hexadecimal y signos
  bool ok = alt.length() > 0 && alt.length() <= 6;
  for (size_t i = 0; i < alt.length(); i++) if (!isDigit(alt[i]) && alt[i] != '.') ok = false;
  char* fin;
  float a = strtof(alt.c_str(), &fin);
  if (!ok || *fin || fin == alt.c_str() || a < 0 || a > 300) return respError(400, "Altura debe estar entre 0 y 300 cm");
  ok = hoj.length() > 0 && hoj.length() <= 3;
  for (size_t i = 0; i < hoj.length(); i++) if (!isDigit(hoj[i])) ok = false;
  if (!ok) return respError(400, "Hojas debe ser un entero entre 0 y 999");
  int car = 0;
  for (size_t i = 0; i < nota.length(); i++) {
    if ((uint8_t)nota[i] < 32 || nota[i] == 127) nota.setCharAt(i, ' ');
    if (((uint8_t)nota[i] & 0xC0) != 0x80) car++;
  }
  if (car > 60 || nota.length() > 240) return respError(400, "La nota admite 60 caracteres");

  long maxId = 0; int n = 0;
  if (LittleFS.exists(R_CREC)) {
    char b[320];
    gF = LittleFS.open(R_CREC, "r");
    while (leerLinea(b, sizeof(b))) if (b[0]) { n++; if (atol(b) > maxId) maxId = atol(b); }
    gF.close();
  }
  if (n >= DASH_MAX_CRECIMIENTO) return respError(409, "Límite de registros: descarga el CSV y borra alguno");
  File f = LittleFS.open(R_CREC, "a");
  char b[320];
  int t = snprintf(b, sizeof(b), "%ld,%s,%.1f,%d,%s\n", maxId + 1, fecha.c_str(), a, (int)hoj.toInt(), nota.c_str());
  ok = f && f.write((uint8_t*)b, t) == (size_t)t;
  f.close();
  medirFs();
  if (!ok) return respError(500, "No se pudo guardar");
  snprintf(b, sizeof(b), "{\"ok\":true,\"id\":%ld}", maxId + 1);
  servidor.send(200, "application/json", b);
}
void apiCrecBorrar() {
  if (!permitido()) return;
  if (!dashFs) return respError(503, "LittleFS no disponible");
  long id = servidor.arg("id").toInt();
  bool esta = false;
  if (id > 0 && LittleFS.exists(R_CREC)) {
    char b[320];
    gF = LittleFS.open(R_CREC, "r");
    while (leerLinea(b, sizeof(b))) if (atol(b) == id) esta = true;
    gF.close();
  }
  if (!esta) return respError(404, "No existe ese registro");
  if (!copiarSin(R_CREC, 0, id)) return respError(500, "No se pudo borrar");
  medirFs();
  respOk();
}
void apiCrecCsv() {
  if (!dashFs) return respError(503, "LittleFS no disponible");
  respCsv("crecimiento.csv");
  sal("id;fecha;altura_cm;hojas;nota\r\n");
  if (LittleFS.exists(R_CREC)) {
    char b[320]; char* p[5];
    gF = LittleFS.open(R_CREC, "r");
    while (!salRota && leerLinea(b, sizeof(b))) {
      if (!crecPartes(b, p)) continue;
      char* punto = strchr(p[2], '.');
      if (punto) *punto = ',';
      sal("%s;%s;%s;%s;\"", p[0], p[1], p[2], p[3]);
      // Una nota que empiece así se ejecutaría como fórmula en Excel
      if (p[4][0] && strchr("=+-@", p[4][0])) sal("'");
      for (char* c = p[4]; *c; c++) sal(*c == '"' ? "\"\"" : "%c", *c);
      sal("\"\r\n");
    }
    gF.close();
  }
  respFin();
}

// ===== API general =====
void apiEstado() {
  respJson();
  uint32_t up = uptimeS();
  sal("{\"listo\":%s,\"uptime_s\":%lu,\"hum_raw\":%d,\"luz_raw\":%d,\"hum_pct\":%d,\"luz_pct\":%d,\"indice\":%d,",
      dashHayMuestra ? "true" : "false", (unsigned long)up, hRaw, lRaw, hPct, lPct, indice);
  sal("\"estado\":%d,\"estado_texto\":\"%s\",\"frase\":", estadoActual, EST_TEXTO[estadoActual]);
  salTexto(FRASES[PERSONALIDAD][estadoActual]);
  sal(",\"horas_sin_regar\":%lu,\"avisos\":[", horasSinRegar());
  bool primero = true;
  for (int i = 0; i < nAlertas; i++) {
    int e = alertas[i];
    if (e == FELIZ) continue;
    sal("%s{\"estado\":%d,\"clave\":\"%s\",\"texto\":\"%s\",\"frase\":", primero ? "" : ",", e, EST_CLAVE[e], EST_TEXTO[e]);
    salTexto(FRASES[PERSONALIDAD][e]);
    sal("}");
    primero = false;
  }
  sal("],\"alertas\":[");
  uint32_t ahora = horaReal() ? (uint32_t)time(nullptr) : 0;
  primero = true;
  for (int e = 0; e < 6; e++) {
    if (!alertaEst[e].sostenida) continue;
    uint32_t d = up - alertaEst[e].desde;
    sal("%s{\"estado\":%d,\"clave\":\"%s\",\"texto\":\"%s\",\"desde_s\":%lu,\"inicio\":%lu}", primero ? "" : ",", e, EST_CLAVE[e],
        EST_TEXTO[e], (unsigned long)d, ahora ? (unsigned long)(ahora - d) : 0UL);
    primero = false;
  }
  sal("],\"resueltas\":[");
  for (int i = 0; i < nResueltas; i++) {
    Resuelta& r = resueltas[i];
    sal("%s{\"estado\":%lu,\"clave\":\"%s\",\"texto\":\"%s\",\"inicio\":%lu,\"fin\":%lu,\"duracion_s\":%lu}", i ? "," : "",
        (unsigned long)r.tipo, EST_CLAVE[r.tipo], EST_TEXTO[r.tipo], (unsigned long)r.inicio, (unsigned long)r.fin, (unsigned long)r.duracion);
  }
  sal("],\"wifi_rssi\":%d,\"ip\":\"%s\",\"hora_real\":%s,\"epoch\":%lu,", WiFi.RSSI(), WiFi.localIP().toString().c_str(),
      horaReal() ? "true" : "false", horaReal() ? (unsigned long)time(nullptr) : 0UL);
  sal("\"fs_ok\":%s,\"fs_usado\":%lu,\"fs_total\":%lu,\"heap_libre\":%lu,\"heap_min\":%lu,\"arranque\":%u}",
      dashFs ? "true" : "false", (unsigned long)dashFsUsado, (unsigned long)dashFsTotal,
      (unsigned long)ESP.getFreeHeap(), (unsigned long)ESP.getMinFreeHeap(), dashArranque);
  respFin();
}
void apiConfig() {
  respJson();
  sal("{\"umbrales\":{\"sed\":%d,\"encharcada\":%d,\"poca_luz\":%d,\"mucha_luz\":%d,\"estres\":%d,\"salto_riego\":%d},",
      UMBRAL_SED, UMBRAL_EXCESO, UMBRAL_POCA_LUZ, UMBRAL_MUCHA_LUZ, UMBRAL_ESTRES, SALTO_RIEGO);
  sal("\"calibracion\":{\"hum_seco\":%d,\"hum_humedo\":%d,\"luz_oscuro_log\":%d,\"luz_claro_log\":%d,\"luz_escala\":\"logaritmica\"},",
      HUM_SECO, HUM_HUMEDO, LUZ_OSCURO_LOG, LUZ_CLARO_LOG);
  sal("\"tiempos\":{\"muestra_ms\":%lu,\"confirmar_ms\":%lu,\"riego_ms\":%lu,\"ms_por_hora\":%lu,\"historial_ms\":%lu,", T_MUESTRA,
      T_CONFIRMAR, T_RIEGO, MS_POR_HORA, DASH_T_HISTORIAL);
  sal("\"alerta_agua_min\":%lu,\"alerta_otras_min\":%lu},\"personalidad\":%d}", (unsigned long)DASH_MIN_ALERTA_AGUA,
      (unsigned long)DASH_MIN_ALERTA_OTRAS, PERSONALIDAD);
  respFin();
}
void apiPagina() {
  salN = 0; salRota = false;
  size_t n = strlen(PAGINA), i = 0;
  servidor.sendHeader("Cache-Control", "no-cache");
  servidor.setContentLength(n);
  servidor.send(200, "text/html; charset=utf-8", "");
  while (i < n && !salRota) {
    size_t t = n - i > sizeof(salBuf) ? sizeof(salBuf) : n - i;
    memcpy(salBuf, PAGINA + i, t);
    salN = t;
    salEnviar();
    i += t;
  }
}
void apiRiego() {
  if (!permitido()) return;
  tUltimoRiego = millis();
  respOk();
}

// ===== Las tres funciones que llama el firmware =====
void dashAlConectar() {
  dashConectado = true;
  if (!dashMdns && MDNS.begin("maceta")) {
    MDNS.addService("http", "tcp", 80);
    dashMdns = true;
  }
  Serial.printf("# Dashboard: http://%s  o  http://maceta.local\n", WiFi.localIP().toString().c_str());
}

void dashboardIniciar() {
  dashFs = LittleFS.begin(true);   // la primera vez formatea (unos segundos)
  if (dashFs) {
    File f = LittleFS.open("/arranque", "r");
    if (f) { dashArranque = f.parseInt(); f.close(); }
    dashArranque++;
    f = LittleFS.open("/arranque", "w");
    if (f) f.println(dashArranque);
    f.close();
  } else Serial.println("# LittleFS no disponible: sin historial");
  if (dashFs) histIniciar();
  alertasIniciar();
  diaIniciar();
  medirFs();

  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setHostname("maceta");
  WiFi.setAutoReconnect(true);
  configTzTime("<-05>5", "pool.ntp.org", "time.google.com");   // America/Bogota
  WiFi.begin(WIFI_SSID, WIFI_CLAVE);
  WiFi.setTxPower(DASH_POTENCIA_WIFI);

  const char* cab[] = { "X-Maceta" };
  servidor.collectHeaders(cab, 1);
  servidor.on("/", HTTP_GET, apiPagina);
  servidor.on("/api/estado", HTTP_GET, apiEstado);
  servidor.on("/api/config", HTTP_GET, apiConfig);
  servidor.on("/api/historial", HTTP_GET, apiHistorial);
  servidor.on("/api/historial.csv", HTTP_GET, apiHistorialCsv);
  servidor.on("/api/diario", HTTP_GET, apiDiario);
  servidor.on("/api/diario.csv", HTTP_GET, apiDiarioCsv);
  servidor.on("/api/crecimiento", HTTP_GET, apiCrecListar);
  servidor.on("/api/crecimiento", HTTP_POST, apiCrecGuardar);
  servidor.on("/api/crecimiento", HTTP_DELETE, apiCrecBorrar);
  servidor.on("/api/crecimiento.csv", HTTP_GET, apiCrecCsv);
  servidor.on("/api/riego", HTTP_POST, apiRiego);
  servidor.onNotFound([]() { respError(404, "Ruta no encontrada"); });
  servidor.begin();
  servidor.enableDelay(false);

  unsigned long t = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t < DASH_T_ESPERA_WIFI) delay(100);
  dashTReintento = millis();
  if (WiFi.status() == WL_CONNECTED) {
    dashAlConectar();
    linea(0, "Abre en celular:");
    linea(1, WiFi.localIP().toString().c_str());
    delay(DASH_T_MOSTRAR_IP);
  } else Serial.println("# WiFi no disponible: sigo sin dashboard y reintento");
}

void dashboardAtender() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!dashConectado) dashAlConectar();
    dashTReintento = millis();
  } else {
    if (dashConectado) { dashConectado = false; Serial.println("# WiFi perdido, reintentando"); }
    if (millis() - dashTReintento >= DASH_T_REINTENTO) {
      dashTReintento = millis();
      WiFi.reconnect();
    }
  }
  servidor.handleClient();
  servidor.soltarInactivo();
  delay(1);   // cede la CPU al WiFi
}

void dashboardRegistrar() {
  dashHayMuestra = true;
  alertasRegistrar();
  diaRegistrar();
  histGuardar();
}
#endif
