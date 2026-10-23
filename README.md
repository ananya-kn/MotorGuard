# MotorGuardddd

Clip-on edge-AI predictive maintenance node for small workshops: vibration + current + temperature -> fault class, health score, time to failure, phone alert.
Vishwakarma Awards 2026-27, Stage 2 (VK26-IITI-AHM-0131), Team Vibronix, Cambridge Institute of Technology, Bengaluru.

## Run the demo with no hardware (2 minutes)
```bash
pip install -r requirements.txt
cd ml && python train.py            # trains on synthetic machines, writes ml/model/ and docs/results/
cd ../server && uvicorn app:app --port 8000
# open http://localhost:8000 then, in another terminal:
python sim_node.py --fault imbalance      # also: misalignment | looseness | bearing | overload
```
Optional phone alerts: `export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...` before starting the server.

## Build the node
1. Wire per `hardware/pinout.md`. BOM in `hardware/BOM.csv`.
2. Arduino IDE: ESP32 board package; libraries Adafruit INA219 (or ADS1X15), OneWire, DallasTemperature.
3. Edit `firmware/motorguard_node/config.h` (WiFi, server IP, node id, current sensor). Flash `motorguard_node.ino`.
4. Print or machine the parts from `cad/out/*.step` (re-run `cad/build_cad.py` after measuring your modules).

## Collect real data and retrain
See `docs/validation_protocol.md`. `tools/collect_serial.py` -> `python ml/train.py --real data/`.

## Verify the code yourself
```bash
sh firmware/tests/run_crosscheck.sh   # C++ features vs Python features (must print worst diff < 2e-3)
python docs/mount_resonance.py        # numbers used on the CAD slide
```

## Layout
`ml/` features, simulator, training | `server/` FastAPI + dashboard + simulator node | `firmware/` ESP32 node + host tests | `cad/` CadQuery -> STEP/STL | `docs/` results, limits, protocol, renders | `hardware/` BOM, pinout | `tools/` serial collector, STL renderer

Read `docs/known_limits.md` before presenting.

> Starter code (simulator, features, server, firmware, CAD scripts) was generated with AI assistance (Claude) and is being adapted, tested and extended by the team on real hardware.
