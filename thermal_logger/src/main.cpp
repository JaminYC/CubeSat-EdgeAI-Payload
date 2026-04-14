/*
 * ESP32 Thermal Logger — Fase 1 (v1.1 — rechazo de spikes EMI)
 * Sensor : MAX6675 (termocupla tipo K)
 * Pines  : SCK=18  CS=5  SO=19
 *
 * Comandos por Serial (115200):
 *   START            — inicia logging
 *   STOP             — detiene logging
 *   RATE <ms>        — periodo de muestreo (200-5000 ms)
 *   MODE RAW         — salida: t_ms,temp_C
 *   MODE FILTER      — salida: t_ms,temp_C,temp_C_filtered
 *   OFFSET <C>       — offset de calibración (ej. OFFSET -2.5)
 *   GAIN <factor>    — factor multiplicativo de calibración
 *   ALPHA <0.0-1.0>  — suavizado EMA (chico=más suave, default=0.10)
 *   SPIKE <C>        — umbral de rechazo de spike (default=15.0 °C, 0=desactivado)
 *   STATS            — muestra conteo de spikes rechazados
 *   RESET            — reinicia tiempo base y filtro
 */

#include <Arduino.h>
#include <MAX6675.h>

// ─── Pines ───────────────────────────────────────────────
static constexpr uint8_t PIN_SCK = 18;
static constexpr uint8_t PIN_CS  =  5;
static constexpr uint8_t PIN_SO  = 19;

// ─── Configuración por defecto ────────────────────────────
static constexpr uint32_t DEFAULT_RATE_MS    = 500;
static constexpr uint32_t MIN_RATE_MS        = 200;
static constexpr uint32_t MAX_RATE_MS        = 5000;
static constexpr float    DEFAULT_EMA_ALPHA  = 0.10f;
static constexpr float    DEFAULT_SPIKE_THR  = 15.0f; // °C — salto máximo permitido vs EMA

// ─── Objeto sensor ────────────────────────────────────────
MAX6675 sensor(PIN_SCK, PIN_CS, PIN_SO);

// ─── Estado global ────────────────────────────────────────
static bool     logging      = false;
static bool     modeFilter   = false;
static uint32_t rateMs       = DEFAULT_RATE_MS;
static float    offsetC      = 0.0f;
static float    gainFactor   = 1.0f;
static float    emaAlpha     = DEFAULT_EMA_ALPHA;
static float    spikeThr     = DEFAULT_SPIKE_THR;  // 0 = sin filtro de spike
static float    emaTemp      = NAN;
static uint32_t lastSample   = 0;
static uint32_t timeBase     = 0;
static uint32_t spikeCount   = 0;   // estadística: spikes rechazados
static uint32_t totalSamples = 0;   // estadística: muestras totales válidas
static String   cmdBuf;

// ─── Prototipos ───────────────────────────────────────────
static void processCommand(String& cmd);
static void printCsvHeader();
static void takeSample();
static void printStats();

// ─────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(500); // MAX6675 necesita ≥500 ms tras power-on

    Serial.println(F("# ESP32 Thermal Logger v1.1"));
    Serial.println(F("# Comandos: START | STOP | RATE <ms> | MODE RAW/FILTER"));
    Serial.println(F("#           GAIN <f> | OFFSET <C> | ALPHA <a> | SPIKE <C>"));
    Serial.println(F("#           STATS | RESET"));
    Serial.printf("# Config: RATE=%lu ms | ALPHA=%.2f | SPIKE=%.1f C\n",
                  rateMs, emaAlpha, spikeThr);
}

// ─────────────────────────────────────────────────────────
void loop() {
    // ── Lectura de comandos serial (no bloqueante) ──
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\n' || c == '\r') {
            cmdBuf.trim();
            if (cmdBuf.length() > 0) {
                processCommand(cmdBuf);
                cmdBuf = "";
            }
        } else {
            cmdBuf += c;
        }
    }

    // ── Muestreo no bloqueante ──
    if (logging && (millis() - lastSample >= rateMs)) {
        lastSample = millis();
        takeSample();
    }
}

// ─── Toma una muestra, aplica rechazo de spike y EMA ─────
static void takeSample() {
    uint32_t t   = millis() - timeBase;
    float    raw = sensor.readCelsius();

    if (isnan(raw)) {
        Serial.printf("# WARN t=%lu thermocouple fault\n", t);
        if (modeFilter) {
            Serial.printf("%lu,NaN,NaN\n", t);
        } else {
            Serial.printf("%lu,NaN\n", t);
        }
        return;
    }

    float temp = (raw * gainFactor) + offsetC;

    // ── Rechazo de spike ─────────────────────────────────
    // Solo rechaza si el EMA ya está inicializado y el umbral está activo
    if (spikeThr > 0.0f && !isnan(emaTemp)) {
        float delta = fabsf(temp - emaTemp);
        if (delta > spikeThr) {
            spikeCount++;
            Serial.printf("# SPIKE rechazado t=%lu raw=%.2f ema=%.2f delta=%.2f C (total=%lu)\n",
                          t, temp, emaTemp, delta, spikeCount);
            // NO actualizamos EMA ni emitimos dato — la muestra se descarta
            return;
        }
    }

    // ── Actualizar EMA ───────────────────────────────────
    if (isnan(emaTemp)) {
        emaTemp = temp; // primera lectura válida: inicializar sin filtrar
    } else {
        emaTemp = emaAlpha * temp + (1.0f - emaAlpha) * emaTemp;
    }

    totalSamples++;

    if (modeFilter) {
        Serial.printf("%lu,%.2f,%.2f\n", t, temp, emaTemp);
    } else {
        Serial.printf("%lu,%.2f\n", t, temp);
    }
}

// ─── Imprime cabecera CSV según modo activo ───────────────
static void printCsvHeader() {
    if (modeFilter) {
        Serial.println(F("t_ms,temp_C,temp_C_filtered"));
    } else {
        Serial.println(F("t_ms,temp_C"));
    }
}

// ─── Estadísticas de calidad ─────────────────────────────
static void printStats() {
    Serial.printf("# STATS: muestras_validas=%lu spikes_rechazados=%lu\n",
                  totalSamples, spikeCount);
    if (totalSamples + spikeCount > 0) {
        float pct = 100.0f * spikeCount / (totalSamples + spikeCount);
        Serial.printf("# STATS: tasa_spike=%.1f%%\n", pct);
    }
    Serial.printf("# CONFIG: RATE=%lu ms | ALPHA=%.3f | SPIKE_THR=%.1f C | OFFSET=%.2f C | GAIN=%.4f\n",
                  rateMs, emaAlpha, spikeThr, offsetC, gainFactor);
}

// ─── Parser de comandos serial ────────────────────────────
static void processCommand(String& cmd) {
    String upper = cmd;
    upper.toUpperCase();

    // ── START ──
    if (upper == "START") {
        if (!logging) {
            logging    = true;
            lastSample = millis() - rateMs;
            Serial.println(F("# Logging STARTED"));
            printCsvHeader();
        } else {
            Serial.println(F("# Ya estaba en logging"));
        }
        return;
    }

    // ── STOP ──
    if (upper == "STOP") {
        logging = false;
        Serial.println(F("# Logging STOPPED"));
        printStats();
        return;
    }

    // ── RESET ──
    if (upper == "RESET") {
        timeBase     = millis();
        emaTemp      = NAN;
        spikeCount   = 0;
        totalSamples = 0;
        Serial.println(F("# Time base, filtro y contadores reiniciados"));
        return;
    }

    // ── STATS ──
    if (upper == "STATS") {
        printStats();
        return;
    }

    // ── RATE <ms> ──
    if (upper.startsWith("RATE ")) {
        long val = upper.substring(5).toInt();
        if (val >= (long)MIN_RATE_MS && val <= (long)MAX_RATE_MS) {
            rateMs = (uint32_t)val;
            Serial.printf("# RATE = %lu ms (%.1f Hz)\n", rateMs, 1000.0f / rateMs);
        } else {
            Serial.printf("# ERROR: RATE debe estar entre %lu y %lu ms\n",
                          MIN_RATE_MS, MAX_RATE_MS);
        }
        return;
    }

    // ── MODE RAW / MODE FILTER ──
    if (upper == "MODE RAW") {
        modeFilter = false;
        Serial.println(F("# Modo: RAW"));
        return;
    }
    if (upper == "MODE FILTER") {
        modeFilter = true;
        Serial.printf("# Modo: FILTER (EMA alpha=%.3f)\n", emaAlpha);
        return;
    }

    // ── GAIN <valor> ──
    if (upper.startsWith("GAIN ")) {
        String valStr = cmd.substring(5);
        valStr.trim();
        gainFactor = valStr.toFloat();
        Serial.printf("# GAIN = %.4f\n", gainFactor);
        return;
    }

    // ── OFFSET <valor> ──
    if (upper.startsWith("OFFSET ")) {
        String valStr = cmd.substring(7);
        valStr.trim();
        offsetC = valStr.toFloat();
        Serial.printf("# OFFSET = %.2f C\n", offsetC);
        return;
    }

    // ── ALPHA <0.0-1.0> ──
    if (upper.startsWith("ALPHA ")) {
        String valStr = cmd.substring(6);
        valStr.trim();
        float val = valStr.toFloat();
        if (val > 0.0f && val <= 1.0f) {
            emaAlpha = val;
            emaTemp  = NAN; // reiniciar EMA al cambiar alpha
            Serial.printf("# ALPHA = %.3f (EMA reiniciado)\n", emaAlpha);
        } else {
            Serial.println(F("# ERROR: ALPHA debe estar entre 0.0 y 1.0 (ej. ALPHA 0.10)"));
        }
        return;
    }

    // ── SPIKE <°C> ──
    if (upper.startsWith("SPIKE ")) {
        String valStr = cmd.substring(6);
        valStr.trim();
        float val = valStr.toFloat();
        if (val >= 0.0f) {
            spikeThr = val;
            if (spikeThr == 0.0f) {
                Serial.println(F("# SPIKE filter DESACTIVADO"));
            } else {
                Serial.printf("# SPIKE threshold = %.1f C\n", spikeThr);
            }
        } else {
            Serial.println(F("# ERROR: SPIKE debe ser >= 0 (0 = desactivar)"));
        }
        return;
    }

    // ── Comando no reconocido ──
    Serial.println(F("# Comandos: START | STOP | RATE <ms> | MODE RAW/FILTER"));
    Serial.println(F("#           GAIN <f> | OFFSET <C> | ALPHA <a> | SPIKE <C> | STATS | RESET"));
}
