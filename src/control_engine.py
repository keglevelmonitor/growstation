"""
GrowStation app
control_engine.py — Evaluates schedules and thermostatic logic to produce relay states
"""

from datetime import datetime, time
from temp_reader import read_temp_f


def _parse_time_str(s):
    """Parse 'HH:MM' or 'H:MM' to (h, m). Returns None on failure."""
    if not s or not isinstance(s, str):
        return None
    parts = s.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h <= 23 and 0 <= m <= 59:
            return (h, m)
    except ValueError:
        pass
    return None


def _in_schedule_window(now_time, windows):
    """
    windows: list of [{"on": "HH:MM", "off": "HH:MM"}, ...]
    Returns True if now_time falls within any on/off window.
    """
    for w in windows:
        on_p = _parse_time_str(w.get("on", ""))
        off_p = _parse_time_str(w.get("off", ""))
        if on_p is None or off_p is None:
            continue
        on_t = time(on_p[0], on_p[1])
        off_t = time(off_p[0], off_p[1])
        if on_t <= off_t:
            if on_t <= now_time <= off_t:
                return True
        else:
            if now_time >= on_t or now_time <= off_t:
                return True
    return False


def _thermo_demand(sensor_id, action, setpoint_f, temp_f):
    """
    Returns True if the thermostat demands ON.
    action: "Heat if below" | "Cool if above"
    temp_f: current temp (float) or None
    """
    if temp_f is None:
        return False
    try:
        sp = float(setpoint_f)
        t = float(temp_f)
    except (TypeError, ValueError):
        return False
    if action == "Heat if below":
        return t < sp
    if action == "Cool if above":
        return t > sp
    return False


def compute_relay_states(settings_manager, temp_reader_func=None, temps_cache=None):
    """
    Returns [bool, bool, bool] for each relay ON/OFF.
    temp_reader_func: optional (sensor_id) -> temp_f, else uses read_temp_f.
    temps_cache: optional dict {sensor_idx: temp_f} — when provided, used instead of reading.
    """
    if temp_reader_func is None:
        temp_reader_func = read_temp_f

    now = datetime.now()
    weekday = now.weekday()  # 0=Mon .. 6=Sun
    now_t = now.time()
    results = [False, False, False]

    temps = {}
    sensor_configs = [
        settings_manager.get_sensor_config(0),
        settings_manager.get_sensor_config(1),
        settings_manager.get_sensor_config(2),
    ]
    for i, sc in enumerate(sensor_configs):
        sid = sc.get("ds18b20_id", "unassigned")
        if sid and sid != "unassigned":
            if temps_cache is not None and i in temps_cache:
                temps[i] = temps_cache[i]
            else:
                temps[i] = temp_reader_func(sid)
        else:
            temps[i] = None

    for relay_idx in range(3):
        cfg = settings_manager.get_relay_config(relay_idx)
        mode = cfg.get("control_mode", "Timer only")
        sched = settings_manager.get_schedule(relay_idx)
        day_windows = sched.get(str(weekday), [])
        in_window = _in_schedule_window(now_t, day_windows)

        sensor_id = cfg.get("sensor_id", "unassigned")
        if sensor_id == "unassigned":
            sensor_idx = None
        else:
            sensor_idx = None
            for i, sc in enumerate(sensor_configs):
                if sc.get("ds18b20_id") == sensor_id:
                    sensor_idx = i
                    break
        temp_f = temps.get(sensor_idx) if sensor_idx is not None else None

        action = cfg.get("thermo_action", "Heat if below")
        setpoint = cfg.get("setpoint_f", 70.0)
        thermo_demand = _thermo_demand(sensor_id, action, setpoint, temp_f)

        if mode == "Timer only":
            results[relay_idx] = in_window
        elif mode == "Thermostatic only":
            results[relay_idx] = thermo_demand
        elif mode == "Both":
            logic = cfg.get("schedule_temp_logic", "AND")
            if logic == "AND":
                results[relay_idx] = in_window and thermo_demand
            else:
                results[relay_idx] = in_window or thermo_demand
        else:
            results[relay_idx] = False

    return results
