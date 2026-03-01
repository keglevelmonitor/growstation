# GrowStation

Grow station relay and temperature control for Raspberry Pi. Controls 3 relays (lights, fans, heaters) with schedules and up to 3 DS18B20 temperature sensors.

## Structure

```
GrowStation/
├── src/
│   ├── main_kivy.py      # Main app
│   ├── growstation.kv    # UI layout
│   ├── settings_manager.py
│   ├── relay_control.py
│   ├── control_engine.py
│   ├── temp_reader.py
│   └── assets/
│       ├── help.txt
│       └── growstation.png   # Optional: add for app icon
├── install.sh
├── install.bat
├── growstation.desktop
├── requirements.txt
├── DESIGN.md
└── README.md
```

## Installation (Raspberry Pi)

```bash
cd GrowStation
chmod +x install.sh
./install.sh
```

Data is stored in `~/growstation-data/`.

## Installation (Windows / Development)

```bash
cd GrowStation
install.bat
```

Or manually:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python src/main_kivy.py
```

## Hardware

- **Relay 1** → GPIO 26 (HEAT pin)
- **Relay 2** → GPIO 20 (COOL pin)
- **Relay 3** → GPIO 21 (AUX/Fan pin)
- DS18B20 sensors on 1-Wire bus

## Icon

Place `growstation.png` in `src/assets/` for the app icon. Without it, the default icon is used.
