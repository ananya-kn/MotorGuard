#pragma once
// ---- edit these ----
#define WIFI_SSID      "your-wifi"
#define WIFI_PASS      "your-password"
#define SERVER_URL     "http://192.168.1.50:8000/ingest"   // PC running server/app.py
#define NODE_ID        "Pump-03"

// Current sensor: INA219 (DC test rig, works on the 12 V motor supply) or SCT-013 + ADS1115 (AC motors)
#define CS_INA219  1
#define CS_SCT013  2
#define CURRENT_SENSOR CS_INA219
#define CT_AMPS_PER_VOLT 30.0f     // SCT-013-030: 30 A <-> 1 V. CALIBRATE against a clamp meter.

// Local (offline) protection
#define RMS_ALARM_G    0.60f       // fallback hard limit if the server is unreachable. Tune on your rig.
#define LOCAL_BASELINE 30          // windows used to learn local baseline for z-score alarm
#define LOCAL_Z_ALARM  6.0f

// Debug: print every raw window over serial for tools/collect_serial.py (disables WiFi sending)
#define RAW_DUMP 0

// Pins (ESP32 DevKit)
#define PIN_SDA 21
#define PIN_SCL 22
#define PIN_DS18B20 4
#define PIN_BUZZER 25
#define PIN_LED 2
