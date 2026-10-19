// MotorGuard node: MPU6050 (vibration) + INA219 or SCT-013/ADS1115 (current) + DS18B20 (temp) -> features -> server.
// Libraries (Library Manager): Adafruit INA219, Adafruit ADS1X15, OneWire, DallasTemperature.
// STATUS: written to match tested Python/C++ feature code; NOT yet run on real hardware. Bring up sensor by sensor.
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include "config.h"
#include "mg_features.h"
#if CURRENT_SENSOR == CS_INA219
#include <Adafruit_INA219.h>
Adafruit_INA219 ina;
#else
#include <Adafruit_ADS1X15.h>
Adafruit_ADS1115 ads;
#endif

#define MPU_ADDR 0x68
static float bx[MG_N], by[MG_N], bz[MG_N], scratch[2 * MG_N], spec[MG_N / 2];
OneWire ow(PIN_DS18B20);
DallasTemperature ds(&ow);
String backlog[20];
int backlogN = 0;
// Welford baseline for local z-score alarm
struct Stat { int n = 0; double m = 0, s = 0; void add(double x) { n++; double d = x - m; m += d / n; s += d * (x - m); } double sd() { return n > 1 ? sqrt(s / (n - 1)) : 1; } };
Stat stRms, stHigh;
int badRun = 0;

void mpuWrite(uint8_t reg, uint8_t val) { Wire.beginTransmission(MPU_ADDR); Wire.write(reg); Wire.write(val); Wire.endTransmission(); }

void mpuInit() {
  mpuWrite(0x6B, 0x00);  // wake
  mpuWrite(0x1A, 0x00);  // DLPF off -> accel bandwidth ~260 Hz, 1 kHz internal rate
  mpuWrite(0x19, 0x00);  // sample-rate divider 0 -> 1 kHz
  mpuWrite(0x1C, 0x08);  // +-4 g -> 8192 LSB/g
}

bool readAccel(float &x, float &y, float &z) {
  Wire.beginTransmission(MPU_ADDR); Wire.write(0x3B); if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(MPU_ADDR, 6) != 6) return false;
  int16_t rx = (Wire.read() << 8) | Wire.read(), ry = (Wire.read() << 8) | Wire.read(), rz = (Wire.read() << 8) | Wire.read();
  x = rx / 8192.0f; y = ry / 8192.0f; z = rz / 8192.0f;
  return true;
}

bool captureWindow() {
  uint32_t t0 = micros();
  for (int i = 0; i < MG_N; i++) {
    while ((uint32_t)(micros() - t0) < (uint32_t)i * 1000) {}
    if (!readAccel(bx[i], by[i], bz[i])) return false;
  }
  return true;
}

float readCurrentRms() {
#if CURRENT_SENSOR == CS_INA219
  double s2 = 0; const int n = 400;
  for (int i = 0; i < n; i++) { float a = ina.getCurrent_mA() / 1000.0f; s2 += a * a; }
  return sqrt(s2 / n);
#else
  const int n = 400; static int16_t buf[400]; double m = 0, s2 = 0;
  for (int i = 0; i < n; i++) { buf[i] = ads.readADC_SingleEnded(0); m += buf[i]; }
  m /= n;
  for (int i = 0; i < n; i++) { double v = (buf[i] - m) * 0.125e-3; s2 += v * v; }  // GAIN_ONE: 0.125 mV/bit
  return sqrt(s2 / n) * CT_AMPS_PER_VOLT;
#endif
}

bool postJson(const String &body) {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http; http.begin(SERVER_URL); http.addHeader("Content-Type", "application/json");
  int code = http.POST(body); http.end();
  return code == 200;
}

void alarmBeep(int n) { for (int i = 0; i < n; i++) { digitalWrite(PIN_BUZZER, HIGH); delay(120); digitalWrite(PIN_BUZZER, LOW); delay(120); } }

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUZZER, OUTPUT); pinMode(PIN_LED, OUTPUT);
  Wire.begin(PIN_SDA, PIN_SCL); Wire.setClock(400000);
  mpuInit(); ds.begin(); ds.setWaitForConversion(false);
#if CURRENT_SENSOR == CS_INA219
  ina.begin(); ina.setCalibration_32V_2A();
#else
  ads.begin(); ads.setGain(GAIN_ONE); ads.setDataRate(RATE_ADS1115_860SPS);
#endif
#if !RAW_DUMP
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
#endif
  Serial.println("MotorGuard node ready");
}

void loop() {
  ds.requestTemperatures();
  if (!captureWindow()) { Serial.println("MPU6050 read failed: check wiring"); delay(500); return; }
  float cur = readCurrentRms();
  float temp = ds.getTempCByIndex(0);
#if RAW_DUMP
  Serial.printf("BEGIN cur_rms=%.3f,temp=%.2f\n", cur, temp);
  for (int i = 0; i < MG_N; i++) Serial.printf("%.5f,%.5f,%.5f\n", bx[i], by[i], bz[i]);
  Serial.println("END"); return;
#endif
  float *axs[3] = {bx, by, bz};
  MGFeatures f = mg_features(axs, scratch, spec);
  // local fallback: hard limit + z-score vs. own baseline
  bool bad = f.rms > RMS_ALARM_G;
  if (stRms.n < LOCAL_BASELINE) { stRms.add(f.rms); stHigh.add(f.e_high); }
  else {
    float z1 = (f.rms - stRms.m) / (stRms.sd() + 1e-6), z2 = (f.e_high - stHigh.m) / (stHigh.sd() + 1e-9);
    bad = bad || z1 > LOCAL_Z_ALARM || z2 > LOCAL_Z_ALARM;
  }
  badRun = bad ? badRun + 1 : 0;
  digitalWrite(PIN_LED, badRun >= 3);
  if (badRun >= 3) alarmBeep(2);
  char js[420];
  snprintf(js, sizeof js, "{\"node_id\":\"%s\",\"rms\":%.5f,\"crest\":%.4f,\"kurt\":%.4f,\"f_run\":%.3f,\"a1x\":%.5f,\"a2x\":%.5f,\"a3x\":%.5f,\"r21\":%.4f,\"e_low\":%.6f,\"e_mid\":%.6f,\"e_high\":%.6f,\"centroid\":%.3f,\"cur_rms\":%.4f,\"temp\":%.2f}",
           NODE_ID, f.rms, f.crest, f.kurt, f.f_run, f.a1x, f.a2x, f.a3x, f.r21, f.e_low, f.e_mid, f.e_high, f.centroid, cur, temp);
  if (postJson(js)) {  // flush backlog after reconnect
    while (backlogN > 0 && postJson(backlog[backlogN - 1])) backlogN--;
  } else if (backlogN < 20) {
    backlog[backlogN++] = js;
    if (WiFi.status() != WL_CONNECTED) WiFi.reconnect();
  }
  Serial.println(js);
}
