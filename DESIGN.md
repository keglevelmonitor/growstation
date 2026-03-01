# GrowStation — UX Design Specification

**Version:** 0.1 (pre-implementation)  
**Last updated:** 2025-03-01

---

## Overview

GrowStation is a Raspberry Pi app for a plant-growing station. It controls **3 relays** (lights, fans, other appliances) via user-adjustable schedules and/or thermostatic control, with support for up to **3 DS18B20 temperature sensors**. UX patterns follow FermVault (dashboard, log, settings; tabbed settings; footer navigation).

---

## Design Decisions (from discovery)

| # | Topic | Choice |
|---|-------|--------|
| 1 | Relay–sensor relationship | **Mixed** — User selects per relay: Timer-only, Thermostatic-only, or Both (schedule + temp) |
| 2 | Relay naming | User-customizable; defaults: Relay 1, Relay 2, Relay 3 |
| 3 | Schedule complexity | **Full flexibility** — multiple on/off windows per day, per day of week |
| 4 | Dashboard priority | **Balanced** — all 3 temps + all 3 relay states visible |
| 5 | Logging | **Detailed** — relay state changes + periodic temp snapshots |
| 6 | Temp display | Flat list with user-customizable sensor names |
| 7 | GPIO pins | **Fixed in code** — not user-configurable |
| 8 | "Both" mode logic | **User-selectable** — AND vs OR between schedule and temp |
| 9 | Schedule UI | **Full flexibility** — multiple windows per day, per day |
| 10 | Schedule copy | **Copy to all days** — button to copy a day's schedule to all other days |
| 11 | Time format | Follow Pi system locale (12h/24h) if possible; fallback 24h |
| 12 | Pin mapping | Relay 1=HEAT(26), Relay 2=COOL(20), Relay 3=AUX(21) |
| 13 | Default relay labels | Relay 1, Relay 2 (Heat), Relay 3 (Fan) |

---

## Screen Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  ScreenManager                                                   │
│  ├── Dashboard (main)  ← default                                 │
│  ├── Log                                                        │
│  └── Settings (TabbedPanel)                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Dashboard Screen

**Purpose:** At-a-glance status of all relays and temps; manual overrides.

### Layout (FermVault-style)

```
┌────────────────────────────────────────────────────────────────────────────┐
│  GrowStation                                          [HEAT] [COOL] [FAN]   │  ← optional status indicators if used
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │ RELAY 1          │  │ RELAY 2          │  │ RELAY 3          │          │
│  │ [Light]          │  │ [Heat]           │  │ [Fan]            │          │
│  │                  │  │                  │  │                  │          │
│  │  ON / OFF        │  │  ON / OFF        │  │  ON / OFF        │          │
│  │  [Toggle]        │  │  [Toggle]        │  │  [Toggle]        │          │
│  │  Mode: Timer     │  │  Mode: Both      │  │  Mode: Thermo    │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ TEMPERATURES                                                         │   │
│  │  Canopy:    72.4°F     Root Zone:  68.1°F     Ambient:   71.2°F     │   │
│  │  (user-customizable names; --.- if sensor missing)                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
├────────────────────────────────────────────────────────────────────────────┤
│  [  SYSTEM LOG  ]  [  SETTINGS  ]  [  HELP  ]                               │
└────────────────────────────────────────────────────────────────────────────┘
```

**Elements:**
- **Relay cards (3):** User label, ON/OFF state, manual toggle, mode badge (Timer / Thermo / Both)
- **Temperature row:** Flat, 3 columns; user-assigned names
- **Footer:** SYSTEM LOG, SETTINGS, HELP

---

## 2. Settings Screen

**Purpose:** Configure relays, schedules, sensors, system options.

### TabbedPanel structure

```
┌────────────────────────────────────────────────────────────────────────────┐
│  [ RELAYS ]  [ SCHEDULES ]  [ SENSORS ]  [ SYSTEM ]                         │
├────────────────────────────────────────────────────────────────────────────┤
│  (Tab content)                                                              │
│  ...                                                                        │
├────────────────────────────────────────────────────────────────────────────┤
│  [ EXIT ]  [ HELP ]  [ RESET/DEFAULTS ]  [ SAVE ]                           │
└────────────────────────────────────────────────────────────────────────────┘
```

### Tab 1: RELAYS

- **Relay 1 / 2 / 3** — each with:
  - **Label** (text input) — e.g. "Light", "Heat", "Fan"; defaults: Relay 1, Relay 2, Relay 3
  - **Control mode** (spinner): `Timer only` | `Thermostatic only` | `Both`
  - If **Thermostatic** or **Both:**
    - **Sensor** (spinner) — which DS18B20 (by user name)
    - **Action** (spinner): `Heat if below` | `Cool if above`
    - **Setpoint** (stepper/slider) — °F or °C
  - If **Both:**
    - **Schedule + Temp logic** (spinner): `AND` | `OR`
      - AND: ON when (in schedule ON window) AND (temp condition met)
      - OR: ON when (in schedule ON window) OR (temp condition met)

### Tab 2: SCHEDULES

- **Per relay, per day of week** (Mon–Sun)
- Each day can have **multiple on/off windows**
- UI pattern: list of windows; add/remove buttons
  - Example: Mon: 6:00–12:00, 14:00–22:00
- Time inputs: follow Pi system locale (12h/24h) if possible; fallback to 24h
- **Copy to all days** — button to copy current relay's schedule for selected day to all other days

**Wireframe concept:**
```
Relay: [Light ▼]
Day:   [Mon ▼]

Window 1:  [06:00] — [12:00]   [Remove]
Window 2:  [14:00] — [22:00]   [Remove]
[+ Add window]

[Copy to all days]
```

### Tab 3: SENSORS

- **Sensor 1 / 2 / 3** — each with:
  - **DS18B20 ID** (spinner) — from scan; "—" if none
  - **Display name** (text input) — e.g. "Canopy", "Root Zone", "Ambient"
- **Scan** button to refresh available sensors

### Tab 4: SYSTEM

- **Temperature units** — °F | °C
- **Relay logic** — Active HIGH | Active LOW
- **Logging interval** — e.g. 5, 10, 15 min for temp snapshots
- **Enable detailed log** — checkbox (relay events + temp snapshots)

---

## 3. Log Screen

**Purpose:** View system log (relay events + temp snapshots).

- **Header:** "SYSTEM LOG"
- **Checkbox:** "Append to growstation-data/system_log.csv"
- **ScrollView** with log text (same pattern as FermVault)
- **Footer:** EXIT, HELP

---

## 4. Data Storage

- **Path:** `growstation-data/` (created at runtime, sibling to app or in home)
- **Files:**
  - `config.json` (or similar) — relay labels, modes, setpoints, schedules, sensor assignments
  - `system_log.csv` — timestamped relay events + temp readings

---

## 5. Implementation Notes

- **Framework:** Kivy (to match FermVault)
- **Hardware:** 3 relays + up to 3 DS18B20; GPIO pins **fixed in code**:
  - Relay 1 → HEAT pin (GPIO 26, Board 37)
  - Relay 2 → COOL pin (GPIO 20, Board 38)
  - Relay 3 → AUX/Fan pin (GPIO 21, Board 40)
- **Default relay labels:** Relay 1, Relay 2 (Heat), Relay 3 (Fan) — user-customizable
- **Deployment:** Same pattern as other apps — install scripts, desktop shortcut; app creates `growstation-data`

---

## 6. Open Items / Future Refinement

- [ ] Default logging interval (e.g. 5 vs 10 min)
- [ ] Help content for each tab

---

*This document serves as the UX spec for implementation. Refinements welcome.*
