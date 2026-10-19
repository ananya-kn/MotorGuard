# MotorGuard wiring (ESP32 DevKit)

| Signal | ESP32 pin | Notes |
|---|---|---|
| I2C SDA | GPIO21 | MPU6050 (0x68), INA219 (0x40) or ADS1115 (0x48) share the bus |
| I2C SCL | GPIO22 | 400 kHz |
| DS18B20 data | GPIO4 | 4.7 k pull-up to 3V3 |
| Buzzer | GPIO25 | active buzzer via small transistor if > 12 mA |
| Status LED | GPIO2 | onboard |
| L298N ENA (PWM) | GPIO26 | test-rig motor speed (add to sketch if you drive the rig from the ESP32) |
| L298N IN1/IN2 | GPIO27 / GPIO14 | direction |

Power: 12 V adapter -> 1 A fuse -> LM2596 set to 5.0 V (set it BEFORE connecting the ESP32) -> ESP32 VIN. Motor supply from the same 12 V rail via the L298N.
INA219 sits in series with the 12 V motor supply (Vin+ from adapter, Vin- to L298N +12V).
SCT-013 (AC path): output through its built-in burden -> bias network to 1.65 V -> ADS1115 A0. Clamp around ONE live conductor only, never both.
Mains work: only with a supervisor, isolated supply and an RCD. For the demo use the DC rig.
