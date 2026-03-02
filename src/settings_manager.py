"""
GrowStation app
settings_manager.py
"""

import json
import os
import threading

SETTINGS_FILE = "growstation_settings.json"

# Default relay labels per DESIGN: Relay 1=Light, Relay 2=Heat, Relay 3=Fan
DEFAULT_RELAY_LABELS = ["Relay 1", "Relay 2", "Relay 3"]
DEFAULT_SENSOR_NAMES = ["Sensor 1", "Sensor 2", "Sensor 3"]


def _default_relay_config(idx):
    """Default config for relay idx (0-based)."""
    return {
        "label": DEFAULT_RELAY_LABELS[idx],
        "control_mode": "Timer only",  # Timer only | Thermostatic only | Both
        "sensor_id": "unassigned",
        "thermo_action": "Heat if below",  # Heat if below | Cool if above
        "setpoint_f": 70.0,
        "schedule_temp_logic": "AND",  # AND | OR (only for Both mode)
    }


def _default_schedule():
    """Default schedule: empty windows for each day (0=Mon..6=Sun)."""
    return {str(d): [] for d in range(7)}


def _default_sensor_config(idx):
    return {
        "ds18b20_id": "unassigned",
        "display_name": DEFAULT_SENSOR_NAMES[idx],
    }


class SettingsManager:
    def _get_default_settings(self):
        return {
            "relay_settings": [
                _default_relay_config(0),
                _default_relay_config(1),
                _default_relay_config(2),
            ],
            "schedules": {
                "relay_0": _default_schedule(),
                "relay_1": _default_schedule(),
                "relay_2": _default_schedule(),
            },
            "sensor_settings": [
                _default_sensor_config(0),
                _default_sensor_config(1),
                _default_sensor_config(2),
            ],
            "system_settings": {
                "temp_units": "F",
                "relay_active_high": False,
                "relay_logic_configured": True,
                "logging_interval_min": 10,
                "system_logging_enabled": True,
                "window_x": -1,
                "window_y": -1,
                "window_width": 800,
                "window_height": 418,
            },
        }

    def __init__(self, settings_file_path=None):
        self.data_dir = os.path.join(os.path.expanduser("~"), "growstation-data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.settings_file = settings_file_path or os.path.join(
            self.data_dir, SETTINGS_FILE
        )
        self.settings = {}
        self._data_lock = threading.RLock()
        self._load_settings()

    def _load_settings(self):
        try:
            with self._data_lock:
                if not os.path.exists(self.settings_file):
                    self.settings = self._get_default_settings()
                    self._save_all_settings()
                else:
                    with open(self.settings_file, "r") as f:
                        self.settings = json.load(f)
                    defaults = self._get_default_settings()
                    self._merge_defaults(self.settings, defaults)
        except Exception as e:
            print(f"[SettingsManager] Error loading {self.settings_file}: {e}")
            self.settings = self._get_default_settings()

    def _merge_defaults(self, current, defaults):
        """Ensure all default keys exist in current."""
        for key, default_val in defaults.items():
            if key not in current:
                current[key] = default_val
            elif isinstance(default_val, dict) and not isinstance(default_val.get("0"), dict):
                for k, v in default_val.items():
                    if k not in current[key]:
                        current[key][k] = v
            elif isinstance(default_val, list):
                for i, item in enumerate(default_val):
                    if i < len(current[key]) and isinstance(item, dict):
                        for k, v in item.items():
                            if k not in current[key][i]:
                                current[key][i][k] = v
                    elif i >= len(current[key]):
                        current[key].append(item)

    def _save_all_settings(self):
        try:
            with self._data_lock:
                with open(self.settings_file, "w", encoding='utf-8') as f:
                    json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"[SettingsManager] Failed to save: {e}")

    def get(self, key, default=None):
        with self._data_lock:
            sys = self.settings.get("system_settings", {})
            if key in sys:
                return sys[key]
            for relay in self.settings.get("relay_settings", []):
                if isinstance(relay, dict) and key in relay:
                    return relay.get(key, default)
            for sensor in self.settings.get("sensor_settings", []):
                if isinstance(sensor, dict) and key in sensor:
                    return sensor.get(key, default)
        return default

    def set(self, key, value):
        with self._data_lock:
            sys = self.settings.get("system_settings", {})
            if key in sys:
                sys[key] = value
                self._save_all_settings()
                return True
            for relay in self.settings.get("relay_settings", []):
                if isinstance(relay, dict) and key in relay:
                    relay[key] = value
                    self._save_all_settings()
                    return True
            for sensor in self.settings.get("sensor_settings", []):
                if isinstance(sensor, dict) and key in sensor:
                    sensor[key] = value
                    self._save_all_settings()
                    return True
        return False

    def get_relay_config(self, idx):
        with self._data_lock:
            relays = self.settings.get("relay_settings", [])
            if 0 <= idx < len(relays):
                return relays[idx].copy()
        return _default_relay_config(idx)

    def set_relay_config(self, idx, config):
        with self._data_lock:
            relays = self.settings.get("relay_settings", [])
            if 0 <= idx < len(relays):
                relays[idx].update(config)
                self._save_all_settings()
                return True
        return False

    def get_schedule(self, relay_idx):
        key = f"relay_{relay_idx}"
        with self._data_lock:
            schedules = self.settings.get("schedules", {})
            return schedules.get(key, _default_schedule()).copy()

    def set_schedule(self, relay_idx, schedule_dict):
        key = f"relay_{relay_idx}"
        with self._data_lock:
            if "schedules" not in self.settings:
                self.settings["schedules"] = {}
            self.settings["schedules"][key] = schedule_dict
            self._save_all_settings()
            return True

    def copy_schedule_to_all_days(self, relay_idx, day_idx):
        """Copy the schedule for one day to all other days."""
        sched = self.get_schedule(relay_idx)
        windows = sched.get(str(day_idx), [])
        new_sched = {str(d): list(windows) for d in range(7)}
        return self.set_schedule(relay_idx, new_sched)

    def get_sensor_config(self, idx):
        with self._data_lock:
            sensors = self.settings.get("sensor_settings", [])
            if 0 <= idx < len(sensors):
                return sensors[idx].copy()
        return _default_sensor_config(idx)

    def set_sensor_config(self, idx, config):
        with self._data_lock:
            sensors = self.settings.get("sensor_settings", [])
            if 0 <= idx < len(sensors):
                sensors[idx].update(config)
                self._save_all_settings()
                return True
        return False

    def get_system_settings(self):
        with self._data_lock:
            return self.settings.get("system_settings", {}).copy()

    def save_system_settings(self, data):
        with self._data_lock:
            sys = self.settings.get("system_settings", {})
            sys.update(data)
            self._save_all_settings()
            return True
