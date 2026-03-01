"""
GrowStation app
temp_reader.py — DS18B20 temperature reading and detection
"""

import glob
import os
import sys

MOCK_TEMPS_F = [72.4, 68.1, 71.2]
MOCK_SENSOR_IDS = ["28-MOCK-SENSOR1", "28-MOCK-SENSOR2", "28-MOCK-SENSOR3"]


def detect_ds18b20_sensors():
    """Returns list of DS18B20 sensor IDs (28-xxxx format)."""
    if sys.platform == "win32":
        return list(MOCK_SENSOR_IDS)
    base_dir = "/sys/bus/w1/devices/"
    if not os.path.exists(base_dir):
        return []
    device_folders = glob.glob(base_dir + "28-*")
    return [os.path.basename(f) for f in device_folders]


def read_temp_f(sensor_id):
    """
    Reads temperature from a DS18B20 sensor. Returns temp in Fahrenheit or None.
    """
    if not sensor_id or sensor_id == "unassigned":
        return None
    if sys.platform == "win32":
        # Mock: cycle through temps by hash of ID
        idx = hash(sensor_id) % 3
        return MOCK_TEMPS_F[idx]
    device_file = f"/sys/bus/w1/devices/{sensor_id}/w1_slave"
    if not os.path.exists(device_file):
        return None
    try:
        with open(device_file, "r") as f:
            lines = f.readlines()
        if lines[0].strip()[-3:] != "YES":
            return None
        equals_pos = lines[1].find("t=")
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2 :]
            temp_c = float(temp_string) / 1000.0
            return temp_c * 9.0 / 5.0 + 32.0
    except Exception as e:
        print(f"[TempReader] Error reading {sensor_id}: {e}")
    return None
