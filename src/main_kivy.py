# GrowStation app — main_kivy.py
import os
import sys
import subprocess
import threading
import signal
import time
import csv
from datetime import datetime

os.environ["SDL_VIDEO_X11_WMCLASS"] = "GrowStation"

from kivy.config import Config
current_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(current_dir, "assets", "evolution.png")
if os.path.exists(icon_path):
    Config.set("kivy", "window_icon", icon_path)

Config.set("graphics", "width", "800")
Config.set("graphics", "height", "417")
Config.set("graphics", "resizable", "0")

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, ListProperty, BooleanProperty, ObjectProperty, NumericProperty
from kivy.uix.popup import Popup
from kivy.clock import Clock, mainthread

try:
    from settings_manager import SettingsManager
    from relay_control import RelayControl
    from control_engine import compute_relay_states
    from temp_reader import read_temp_f, detect_ds18b20_sensors
except ImportError as e:
    print(f"GrowStation Import Error: {e}")
    SettingsManager = None
    RelayControl = None


def failsafe_cleanup():
    try:
        app = App.get_running_app()
        if app and hasattr(app, "relay_control") and app.relay_control:
            app.relay_control.cleanup_gpio()
    except Exception:
        pass


def handle_signal(signum, frame):
    failsafe_cleanup()
    os._exit(0)


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)
if hasattr(signal, "SIGHUP"):
    signal.signal(signal.SIGHUP, handle_signal)


class DashboardScreen(Screen):
    pass


class LogScreen(Screen):
    pass


class SettingsScreen(Screen):
    """Manages Settings tabs and matching footer (KegLevel Lite pattern)."""

    def set_active_tab(self, tab_code):
        """Switch content and footer to the given tab. tab_code: schedules, relays, sensors, system, updates, about"""
        tab_map = {
            "schedules": ("btn_schedules", "tab_schedules", "footer_schedules"),
            "relays": ("btn_relays", "tab_relays", "footer_relays"),
            "sensors": ("btn_sensors", "tab_sensors", "footer_sensors"),
            "system": ("btn_system", "tab_system", "footer_system"),
            "updates": ("btn_updates", "tab_updates", "footer_updates"),
            "about": ("btn_about", "tab_about", "footer_about"),
        }
        if tab_code not in tab_map:
            return
        target_btn, target_content, target_footer = tab_map[tab_code]
        self.ids.settings_content.current = target_content
        self.ids.settings_footer.current = target_footer
        for code, (btn_id, _, _) in tab_map.items():
            if btn_id in self.ids:
                self.ids[btn_id].state = "down" if code == tab_code else "normal"


class DirtyPopup(Popup):
    pass


class GrowStationApp(App):
    col_theme_blue = ListProperty([0.2, 0.8, 1, 1])
    log_text = StringProperty("[System] GrowStation initializing.\n")
    temp_units = StringProperty("F")
    system_logging_enabled = BooleanProperty(True)
    is_settings_dirty = BooleanProperty(False)
    available_sensors = ListProperty(["unassigned"])
    staged_changes = {}
    relay_labels = ListProperty(["Relay 1", "Relay 2", "Relay 3"])
    relay_states = ListProperty([False, False, False])
    relay_modes = ListProperty(["Timer", "Timer", "Timer"])
    relay_control_mode_0 = StringProperty("Timer only")
    relay_control_mode_1 = StringProperty("Timer only")
    relay_control_mode_2 = StringProperty("Timer only")
    temp_1 = StringProperty("--.-")
    temp_2 = StringProperty("--.-")
    temp_3 = StringProperty("--.-")
    temp_name_1 = StringProperty("Sensor 1")
    temp_name_2 = StringProperty("Sensor 2")
    temp_name_3 = StringProperty("Sensor 3")
    sensor_id_1 = StringProperty("unassigned")
    sensor_id_2 = StringProperty("unassigned")
    sensor_id_3 = StringProperty("unassigned")
    relay_active_high = BooleanProperty(False)
    logging_interval_min = StringProperty("10")
    sched_on_0 = NumericProperty(0)
    sched_off_0 = NumericProperty(0)
    sched_on_1 = NumericProperty(0)
    sched_off_1 = NumericProperty(0)
    sched_on_2 = NumericProperty(0)
    sched_off_2 = NumericProperty(0)
    # Relay operational mode: "schedule" | "skip" | "manual"
    relay_op_mode_0 = StringProperty("schedule")
    relay_op_mode_1 = StringProperty("schedule")
    relay_op_mode_2 = StringProperty("schedule")
    # Next scheduled action per relay: "--" | "ON" | "OFF"
    relay_next_action_0 = StringProperty("--")
    relay_next_action_1 = StringProperty("--")
    relay_next_action_2 = StringProperty("--")
    # Time of next scheduled action: "--:--" | "HH:MM"
    relay_next_time_0 = StringProperty("--:--")
    relay_next_time_1 = StringProperty("--:--")
    relay_next_time_2 = StringProperty("--:--")
    # State used when in SKIP or MANUAL mode
    relay_skip_state_0 = BooleanProperty(False)
    relay_skip_state_1 = BooleanProperty(False)
    relay_skip_state_2 = BooleanProperty(False)
    relay_manual_state_0 = BooleanProperty(False)
    relay_manual_state_1 = BooleanProperty(False)
    relay_manual_state_2 = BooleanProperty(False)
    update_log_text = StringProperty("Click CHECK to check for app updates.\n")
    is_update_available = BooleanProperty(False)
    is_install_successful = BooleanProperty(False)
    settings_manager = ObjectProperty(None)
    relay_control = ObjectProperty(None)
    _tick_interval = None
    _last_log_time = 0.0
    _last_temp_read_time = 0.0
    _cached_temps = {}
    _prev_schedule_states = [None, None, None]
    TEMP_READ_INTERVAL = 5.0  # seconds — DS18B20 reads are slow; avoid blocking UI

    def dismiss_splash(self, dt=None):
        if hasattr(self, "splash_queue") and self.splash_queue:
            self.splash_queue.put("STOP")

    @mainthread
    def log_system_message(self, message):
        ts = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        self.log_text += f"{ts} {message}\n"
        if len(self.log_text) > 5000:
            self.log_text = self.log_text[-4000:]
        if self.system_logging_enabled and hasattr(self, "settings_manager"):
            try:
                data_dir = self.settings_manager.data_dir
                log_path = os.path.join(data_dir, "system_log.csv")
                file_exists = os.path.isfile(log_path)
                with open(log_path, "a", newline="", encoding="utf-8") as f:
                    if not file_exists:
                        f.write("Timestamp,Action\n")
                    clean = message.replace('"', '""')
                    f.write(f'"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}","{clean}"\n')
            except Exception as e:
                print(f"Log write error: {e}")

    def _read_all_temps(self):
        """Read all assigned sensors once. Returns {sensor_idx: temp_f}."""
        if not self.settings_manager:
            return {}
        temps = {}
        for i in range(3):
            sc = self.settings_manager.get_sensor_config(i)
            sid = sc.get("ds18b20_id", "unassigned")
            if sid and sid != "unassigned":
                temps[i] = read_temp_f(sid)
            else:
                temps[i] = None
        return temps

    def _write_temp_snapshot(self):
        if not self.settings_manager or not self.system_logging_enabled:
            return
        try:
            temps = self._cached_temps if self._cached_temps else self._read_all_temps()
            parts = []
            for i in range(3):
                sc = self.settings_manager.get_sensor_config(i)
                name = sc.get("display_name", f"Sensor {i+1}")
                t = temps.get(i)
                parts.append(f"{name}={t:.1f}" if t is not None else f"{name}=--.-")
            msg = "Temp snapshot: " + ", ".join(parts)
            self.log_system_message(msg)
        except Exception as e:
            print(f"Temp snapshot error: {e}")

    def load_kv(self, filename=None):
        """Suppress Kivy's automatic KV discovery; we load manually in build() exactly once."""
        pass

    def build(self):
        self.title = "GrowStation"
        kv_path = os.path.join(current_dir, "growstation.kv")
        if os.path.exists(kv_path):
            root = Builder.load_file(kv_path)
        else:
            from kivy.uix.label import Label
            root = Label(text="growstation.kv not found", font_size="24sp")
        self.sm = root if hasattr(root, "current") else None
        Clock.schedule_once(self._start_backend, 0.2)
        return root

    def _start_backend(self, dt=None):
        if SettingsManager is None or RelayControl is None:
            self.log_system_message("BACKEND ERROR: Modules not found.")
            return
        try:
            self.log_system_message("Initializing backend...")
            self.settings_manager = SettingsManager()
            self.relay_control = RelayControl(self.settings_manager)
            self.relay_control.set_logger(self.log_system_message)
            self._refresh_ui_from_settings()
            self._restore_window_position()
            self._cached_temps = self._read_all_temps()
            self._last_temp_read_time = time.time()
            self._tick_interval = Clock.schedule_interval(self._tick, 1.0)
            self.log_system_message("Backend initialized.")
        except Exception as e:
            self.log_system_message(f"CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()

    def _tick(self, dt):
        if not self.settings_manager or not self.relay_control:
            return
        now = time.time()
        # Read temps only every TEMP_READ_INTERVAL seconds (DS18B20 I/O blocks main thread)
        if now - self._last_temp_read_time >= self.TEMP_READ_INTERVAL:
            self._cached_temps = self._read_all_temps()
            self._last_temp_read_time = now
        schedule_states = compute_relay_states(self.settings_manager, temps_cache=self._cached_temps)
        final_states = list(schedule_states)
        for i in range(3):
            sched_state = bool(schedule_states[i])
            mode = getattr(self, f"relay_op_mode_{i}", "schedule")
            if mode == "schedule":
                final_states[i] = sched_state
            elif mode == "skip":
                skip_st = bool(getattr(self, f"relay_skip_state_{i}", False))
                prev = self._prev_schedule_states[i]
                # Auto-clear SKIP when schedule transitions to match the override state
                if prev is not None and prev != sched_state and sched_state == skip_st:
                    setattr(self, f"relay_op_mode_{i}", "schedule")
                    final_states[i] = sched_state
                else:
                    final_states[i] = skip_st
            elif mode == "manual":
                final_states[i] = bool(getattr(self, f"relay_manual_state_{i}", False))
            self._prev_schedule_states[i] = sched_state
        self.relay_control.set_relay_states_direct(final_states)
        for i in range(3):
            self.relay_states[i] = self.relay_control.is_relay_on(i)
        self._update_temps()
        self._update_relay_labels_and_modes()
        self._update_next_schedule_actions()
        interval_min = float(self.logging_interval_min or 10)
        if self.system_logging_enabled and interval_min > 0 and (now - self._last_log_time) >= interval_min * 60:
            self._last_log_time = now
            self._write_temp_snapshot()

    def _update_temps(self):
        for i in range(3):
            sc = self.settings_manager.get_sensor_config(i)
            t = self._cached_temps.get(i) if self._cached_temps else None
            if t is not None:
                if self.temp_units == "C":
                    t = (t - 32) * 5 / 9
                setattr(self, f"temp_{i+1}", f"{t:.1f}")
            else:
                setattr(self, f"temp_{i+1}", "--.-")
            setattr(self, f"temp_name_{i+1}", sc.get("display_name", f"Sensor {i+1}"))

    def _update_next_schedule_actions(self):
        """Compute the next scheduled ON or OFF for each relay and update display properties."""
        now = datetime.now()
        now_mins = now.hour * 60 + now.minute
        for i in range(3):
            on_slot = int(getattr(self, f"sched_on_{i}", 0))
            off_slot = int(getattr(self, f"sched_off_{i}", 0))
            # No schedule set, or always-on sentinel (both sliders at max)
            if on_slot == 0 or off_slot == 0 or (on_slot == 47 and off_slot == 47):
                setattr(self, f"relay_next_action_{i}", "--")
                setattr(self, f"relay_next_time_{i}", "--:--")
                continue
            on_mins = on_slot * 30
            off_mins = off_slot * 30
            if now_mins < on_mins:
                # Before the ON time today — next action is ON
                setattr(self, f"relay_next_action_{i}", "ON")
                setattr(self, f"relay_next_time_{i}", f"{on_mins // 60:02d}:{on_mins % 60:02d}")
            elif now_mins < off_mins:
                # Inside the ON window — next action is OFF
                setattr(self, f"relay_next_action_{i}", "OFF")
                setattr(self, f"relay_next_time_{i}", f"{off_mins // 60:02d}:{off_mins % 60:02d}")
            else:
                # Past the OFF time — next action is ON (tomorrow, show time only)
                setattr(self, f"relay_next_action_{i}", "ON")
                setattr(self, f"relay_next_time_{i}", f"{on_mins // 60:02d}:{on_mins % 60:02d}")

    def _update_relay_labels_and_modes(self):
        for i in range(3):
            cfg = self.settings_manager.get_relay_config(i)
            self.relay_labels[i] = cfg.get("label", f"Relay {i+1}")
            m = cfg.get("control_mode", "Timer only")
            if m == "Timer only":
                self.relay_modes[i] = "Timer"
            elif m == "Thermostatic only":
                self.relay_modes[i] = "Thermo"
            else:
                self.relay_modes[i] = "Both"

    def _refresh_ui_from_settings(self):
        if not self.settings_manager:
            return
        sys_settings = self.settings_manager.get_system_settings()
        self.temp_units = sys_settings.get("temp_units", "F")
        self.relay_active_high = sys_settings.get("relay_active_high", False)
        self.system_logging_enabled = sys_settings.get("system_logging_enabled", True)
        self.logging_interval_min = str(sys_settings.get("logging_interval_min", 10))
        for i in range(3):
            cfg = self.settings_manager.get_relay_config(i)
            self.relay_labels[i] = cfg.get("label", f"Relay {i+1}")
            m = cfg.get("control_mode", "Timer only")
            self.relay_modes[i] = "Timer" if m == "Timer only" else ("Thermo" if m == "Thermostatic only" else "Both")
            setattr(self, f"relay_control_mode_{i}", m)
            # Always start in SCHEDULE mode on boot regardless of last-saved mode
            setattr(self, f"relay_op_mode_{i}", "schedule")
            setattr(self, f"relay_manual_state_{i}", bool(cfg.get("manual_state", False)))
        for i in range(3):
            sc = self.settings_manager.get_sensor_config(i)
            setattr(self, f"temp_name_{i+1}", sc.get("display_name", f"Sensor {i+1}"))
            setattr(self, f"sensor_id_{i+1}", sc.get("ds18b20_id", "unassigned"))
        for i in range(3):
            sched = self.settings_manager.get_schedule(i)
            windows = sched.get("0", [])
            if windows:
                w = windows[0]
                on_str = w.get("on", "")
                off_str = w.get("off", "")
                # "00:00"/"23:59" is the always-on sentinel → both sliders at max (47)
                if on_str == "00:00" and off_str == "23:59":
                    on_slot, off_slot = 47, 47
                else:
                    on_slot = self._time_to_slot(on_str)
                    off_slot = self._time_to_slot(off_str)
            else:
                on_slot, off_slot = 0, 0
            setattr(self, f"sched_on_{i}", on_slot)
            setattr(self, f"sched_off_{i}", off_slot)
        self._update_temps()

    @staticmethod
    def _time_to_slot(time_str):
        """Convert HH:MM string to 30-min slot index (0-47). 0 = disabled."""
        if not time_str or ":" not in time_str:
            return 0
        try:
            h, m = map(int, time_str.split(":"))
            return max(0, min(47, (h * 60 + m) // 30))
        except (ValueError, TypeError):
            return 0

    def slot_to_time(self, slot):
        """Convert 30-min slot index (0-47) to display string. 0 = OFF."""
        slot = int(slot)
        if slot == 0:
            return "-- OFF --"
        mins = slot * 30
        return f"{mins // 60:02d}:{mins % 60:02d}"

    def set_sched_on(self, relay_idx, slot):
        setattr(self, f"sched_on_{relay_idx}", slot)
        self.stage_setting(f"schedule_on_{relay_idx}", slot)

    def set_sched_off(self, relay_idx, slot):
        setattr(self, f"sched_off_{relay_idx}", slot)
        self.stage_setting(f"schedule_off_{relay_idx}", slot)

    def go_to_screen(self, name, direction="left"):
        if self.sm:
            self.sm.current = name

    def _get_sensor_id_ui(self, i):
        """Get sensor ID from UI; prefer spinner.text (Spinner on_text may not fire)."""
        try:
            settings = (self.sm.ids.get("settings") if self.sm else None)
            if settings:
                sp = settings.ids.get(f"sensor_id_spinner_{i+1}")
                if sp and sp.text:
                    return str(sp.text)
        except Exception:
            pass
        return (getattr(self, f"sensor_id_{i+1}", None) or "unassigned")

    def _settings_ui_differs_from_saved(self):
        """
        Compare current UI state to saved settings. Handles Spinner on_text not firing.
        Returns True if any Setting differs (unsaved changes).
        """
        try:
            if not self.settings_manager:
                return False
            for i in range(3):
                sc = self.settings_manager.get_sensor_config(i)
                saved_id = sc.get("ds18b20_id", "unassigned") or "unassigned"
                saved_name = sc.get("display_name", f"Sensor {i+1}")
                ui_id = self._get_sensor_id_ui(i)
                ui_name = getattr(self, f"temp_name_{i+1}", f"Sensor {i+1}")
                if str(ui_id) != str(saved_id) or str(ui_name) != str(saved_name):
                    return True
            for i in range(3):
                cfg = self.settings_manager.get_relay_config(i)
                saved_label = cfg.get("label", f"Relay {i+1}")
                saved_mode = cfg.get("control_mode", "Timer only")
                if (self.relay_labels[i] != saved_label or
                        getattr(self, f"relay_control_mode_{i}", saved_mode) != saved_mode):
                    return True
            sys_settings = self.settings_manager.get_system_settings()
            if (self.temp_units != sys_settings.get("temp_units", "F") or
                    self.relay_active_high != sys_settings.get("relay_active_high", False) or
                    str(self.logging_interval_min) != str(sys_settings.get("logging_interval_min", 10)) or
                    self.system_logging_enabled != sys_settings.get("system_logging_enabled", True)):
                return True
            return False
        except Exception:
            return True  # fail-safe: show popup if diff check errors

    def _save_ui_to_settings(self):
        """Persist current UI state to settings manager (for SAVE & CONTINUE)."""
        if not self.settings_manager:
            return
        for i in range(3):
            cfg = self.settings_manager.get_sensor_config(i)
            cfg["ds18b20_id"] = self._get_sensor_id_ui(i) or "unassigned"
            cfg["display_name"] = getattr(self, f"temp_name_{i+1}", f"Sensor {i+1}")
            self.settings_manager.set_sensor_config(i, cfg)
        for i in range(3):
            cfg = self.settings_manager.get_relay_config(i)
            cfg["label"] = self.relay_labels[i]
            cfg["control_mode"] = getattr(self, f"relay_control_mode_{i}", "Timer only")
            self.settings_manager.set_relay_config(i, cfg)
        try:
            lim = int(float(self.logging_interval_min or 10))
        except (ValueError, TypeError):
            lim = 10
        self.settings_manager.save_system_settings({
            "temp_units": self.temp_units,
            "relay_active_high": self.relay_active_high,
            "logging_interval_min": lim,
            "system_logging_enabled": self.system_logging_enabled,
        })
        self.log_system_message("Settings saved.")

    def _open_dirty_popup(self, dt):
        """Deferred popup open; avoids touch/event conflicts when called from button release."""
        try:
            DirtyPopup().open()
        except Exception as e:
            self.log_system_message(f"Popup error: {e}")
            import traceback
            traceback.print_exc()

    def attempt_exit_settings(self, tab_name="none"):
        # Diff-based check: Spinner on_text may not fire on some platforms
        if self.is_settings_dirty or self.staged_changes or self._settings_ui_differs_from_saved():
            # Defer popup to next frame; avoids crash when opening from button on_release
            Clock.schedule_once(self._open_dirty_popup, 0)
        else:
            self.go_to_screen("dashboard")

    def discard_changes(self):
        self.staged_changes.clear()
        self.is_settings_dirty = False
        self._refresh_ui_from_settings()
        self.go_to_screen("dashboard")

    def save_and_continue(self):
        self._save_ui_to_settings()
        self.staged_changes.clear()
        self.is_settings_dirty = False
        self.go_to_screen("dashboard")

    def save_current_tab(self, tab_name="none"):
        self._save_staged_changes()
        self.staged_changes.clear()
        self.is_settings_dirty = False
        self._refresh_ui_from_settings()

    def _save_staged_changes(self):
        if not self.settings_manager:
            return
        # System-setting keys must be checked FIRST — "relay_active_high" starts with
        # "relay_" so it would otherwise crash in the relay-config branch below.
        _system_keys = {"temp_units", "relay_active_high", "logging_interval_min", "system_logging_enabled"}
        for key, val in self.staged_changes.items():
            if key in _system_keys:
                pass  # handled in the dedicated system-settings pass below
            elif key.startswith("relay_"):
                parts = key.split("_")
                if len(parts) >= 3:
                    idx = int(parts[1])
                    field = "_".join(parts[2:])
                    cfg = self.settings_manager.get_relay_config(idx)
                    cfg[field] = val
                    self.settings_manager.set_relay_config(idx, cfg)
            elif key.startswith("sensor_"):
                parts = key.split("_")
                if len(parts) >= 3:
                    idx = int(parts[1])
                    field = "_".join(parts[2:])
                    cfg = self.settings_manager.get_sensor_config(idx)
                    cfg[field] = val
                    self.settings_manager.set_sensor_config(idx, cfg)
        # Now handle system settings (separate pass to avoid prefix-collision above)
        for key, val in self.staged_changes.items():
            if key in _system_keys:
                v = val
                if key == "logging_interval_min":
                    try:
                        v = int(float(val))
                    except (ValueError, TypeError):
                        v = 10
                elif key == "system_logging_enabled":
                    v = bool(val)
                self.settings_manager.save_system_settings({key: v})
        # Save schedule changes: collect on/off slots per relay and write to all 7 days
        sched_dirty = {i: {} for i in range(3)}
        for key, val in self.staged_changes.items():
            if key.startswith("schedule_on_"):
                sched_dirty[int(key[-1])]["on"] = int(val)
            elif key.startswith("schedule_off_"):
                sched_dirty[int(key[-1])]["off"] = int(val)
        for i, changes in sched_dirty.items():
            if not changes:
                continue
            on_slot = changes.get("on", getattr(self, f"sched_on_{i}", 0))
            off_slot = changes.get("off", getattr(self, f"sched_off_{i}", 0))
            if on_slot == 47 and off_slot == 47:
                # Both sliders fully right = always on sentinel
                windows = [{"on": "00:00", "off": "23:59"}]
            elif on_slot == 0 or off_slot == 0:
                windows = []
            else:
                on_m, off_m = on_slot * 30, off_slot * 30
                windows = [{"on": f"{on_m // 60:02d}:{on_m % 60:02d}",
                            "off": f"{off_m // 60:02d}:{off_m % 60:02d}"}]
            self.settings_manager.set_schedule(i, {str(d): list(windows) for d in range(7)})
        self.log_system_message("Settings saved.")

    def stage_setting(self, key, value):
        self.staged_changes[key] = value
        self.is_settings_dirty = True

    def set_relay_op_mode(self, relay_idx, mode):
        """Switch relay to 'schedule', 'skip', or 'manual' mode.
        Guard against touch-propagation from other screens (NoTransition is instant)."""
        if relay_idx < 0 or relay_idx > 2:
            return
        if self.sm and self.sm.current != 'dashboard':
            return
        current_state = bool(self.relay_states[relay_idx]) if relay_idx < len(self.relay_states) else False
        setattr(self, f"relay_op_mode_{relay_idx}", mode)
        if mode == "skip":
            setattr(self, f"relay_skip_state_{relay_idx}", not current_state)
        elif mode == "manual":
            # Toggle on every press — same pattern as SKIP, but no auto-clear
            setattr(self, f"relay_manual_state_{relay_idx}", not current_state)
        self.log_system_message(f"Relay {relay_idx + 1} → {mode.upper()} mode")

    def relay_on_off_press(self, relay_idx):
        """Toggle ON/OFF while in SKIP or MANUAL mode. No-op in SCHEDULE mode or non-dashboard screens."""
        if relay_idx < 0 or relay_idx > 2:
            return
        if self.sm and self.sm.current != 'dashboard':
            return
        mode = getattr(self, f"relay_op_mode_{relay_idx}", "schedule")
        if mode == "skip":
            current = bool(getattr(self, f"relay_skip_state_{relay_idx}", False))
            setattr(self, f"relay_skip_state_{relay_idx}", not current)
        elif mode == "manual":
            current = bool(getattr(self, f"relay_manual_state_{relay_idx}", False))
            setattr(self, f"relay_manual_state_{relay_idx}", not current)

    def scan_sensors(self):
        found = detect_ds18b20_sensors()
        self.available_sensors = ["unassigned"] + found
        self.log_system_message(f"Sensor scan: found {len(found)} DS18B20.")
        return found

    def reset_defaults(self, tab_name="none"):
        # Minimal reset: just refresh from disk (no full factory reset for now)
        self._refresh_ui_from_settings()
        self.staged_changes.clear()
        self.is_settings_dirty = False
        self.log_system_message("Defaults refreshed.")

    def check_for_updates(self):
        self.update_log_text = "Checking for updates...\n"
        self.is_update_available = False
        self.is_install_successful = False

        def _check():
            try:
                src_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(src_dir)
                subprocess.check_output(["git", "fetch"], cwd=project_root, stderr=subprocess.STDOUT)
                status = subprocess.check_output(["git", "status", "-uno"], cwd=project_root, text=True)

                def update_ui(dt):
                    if "behind" in status:
                        self.update_log_text += "\n[UPDATE AVAILABLE]\nA new version is available on GitHub.\nClick INSTALL to proceed."
                        self.is_update_available = True
                    elif "up to date" in status:
                        self.update_log_text += "\n[SYSTEM IS CURRENT]\nYou are running the latest version."
                    else:
                        self.update_log_text += f"\n[STATUS UNKNOWN]\nGit status returned:\n{status}"
                Clock.schedule_once(update_ui, 0)
            except Exception as e:
                err_msg = str(e)
                def report_err(dt):
                    self.update_log_text += f"\n[ERROR] Check failed:\n{err_msg}"
                Clock.schedule_once(report_err, 0)

        threading.Thread(target=_check, daemon=True).start()

    def run_update_script(self):
        self.update_log_text += "\n\n[STARTING INSTALLATION]...\n"
        self.is_update_available = False

        def _install():
            script_url = "https://github.com/keglevelmonitor/growstation/raw/main/update.sh"
            try:
                src_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(src_dir)
                local_script_path = os.path.join(project_root, "update.sh")
                Clock.schedule_once(lambda dt: self._append_update_log(f"Downloading update script...\n"), 0)
                subprocess.run(["curl", "-L", "-o", local_script_path, script_url], check=True)
                subprocess.run(["chmod", "+x", local_script_path], check=True)
                Clock.schedule_once(lambda dt: self._append_update_log("Executing update.sh...\n"), 0)
                process = subprocess.Popen(
                    ["./update.sh"],
                    cwd=project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                for line in process.stdout:
                    Clock.schedule_once(lambda dt, l=line: self._append_update_log(l), 0)
                process.wait()
                if process.returncode == 0:
                    Clock.schedule_once(lambda dt: self._append_update_log("\n[SUCCESS] Update finished.\nClick RESTART APP to apply changes."), 0)
                    self.is_install_successful = True
                else:
                    Clock.schedule_once(lambda dt: self._append_update_log(f"\n[FAILURE] Script exited with code {process.returncode}"), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self._append_update_log(f"\n[CRITICAL ERROR] {str(e)}"), 0)

        threading.Thread(target=_install, daemon=True).start()

    def _append_update_log(self, text):
        self.update_log_text += text

    def _restore_window_position(self):
        """Restore last-saved window position and size."""
        try:
            from kivy.core.window import Window
            sys_settings = self.settings_manager.get_system_settings()
            x = sys_settings.get("window_x", -1)
            y = sys_settings.get("window_y", -1)
            w = sys_settings.get("window_width", 800)
            h = sys_settings.get("window_height", 417)
            if x != -1 and y != -1:
                Window.left = int(x)
                Window.top = int(y)
            if w > 0 and h > 0:
                Window.size = (int(w), int(h))
            self.log_system_message(f"Window: pos({x},{y}) size({w}x{h})")
        except Exception as e:
            print(f"[Window] Restore error: {e}")

    def on_stop(self):
        """Save window position/size, relay modes, and clean up on app close."""
        try:
            from kivy.core.window import Window
            if self.settings_manager:
                self.settings_manager.save_system_settings({
                    "window_x": Window.left,
                    "window_y": Window.top,
                    "window_width": Window.size[0],
                    "window_height": Window.size[1],
                })
                print(f"[App] Window saved: pos({Window.left},{Window.top}) size({Window.size})")
        except Exception as e:
            print(f"[App] Window save error: {e}")
        # Persist relay operational modes and manual states (skip reverts to schedule)
        try:
            if self.settings_manager:
                for i in range(3):
                    cfg = self.settings_manager.get_relay_config(i)
                    mode = getattr(self, f"relay_op_mode_{i}", "schedule")
                    cfg["op_mode"] = "schedule" if mode == "skip" else mode
                    cfg["manual_state"] = bool(getattr(self, f"relay_manual_state_{i}", False))
                    self.settings_manager.set_relay_config(i, cfg)
        except Exception as e:
            print(f"[App] Relay mode save error: {e}")
        try:
            if self.relay_control:
                self.relay_control.cleanup_gpio()
        except Exception:
            pass

    def restart_application(self):
        self.log_system_message("RESTARTING APPLICATION...")
        try:
            if hasattr(self, "relay_control") and self.relay_control:
                self.relay_control.cleanup_gpio()
        except Exception as e:
            print(f"[System] Restart cleanup warning: {e}")
        python = sys.executable
        script = os.path.abspath(sys.argv[0])
        args = sys.argv[1:]
        os.execv(python, [python, script] + args)


def main():
    GrowStationApp().run()


if __name__ == "__main__":
    main()
