"""
GrowStation app
relay_control.py — 3 independent relays. Pins match FermVault: Relay1=Heat, Relay2=Cool, Relay3=Fan
"""

import threading
import time
import os
import sys

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    IS_RASPBERRY_PI = True
except (ImportError, RuntimeError):
    IS_RASPBERRY_PI = False

    class MockGPIO:
        BCM = 11
        HIGH = 1
        LOW = 0
        IN = 1
        OUT = 0
        _pin_state = {}

        @classmethod
        def setmode(cls, mode): pass

        @classmethod
        def setwarnings(cls, flag): pass

        @classmethod
        def setup(cls, pin, mode, pull_up_down=None):
            if mode == cls.OUT and pin not in cls._pin_state:
                cls._pin_state[pin] = cls.LOW

        @classmethod
        def output(cls, pin, state):
            cls._pin_state[pin] = state

        @classmethod
        def input(cls, pin):
            return cls._pin_state.get(pin, cls.LOW)

        @classmethod
        def cleanup(cls):
            cls._pin_state.clear()

    GPIO = MockGPIO

# Pin mapping per DESIGN: Relay 1=HEAT(26), Relay 2=COOL(20), Relay 3=AUX/Fan(21)
RELAY_PINS = {
    "Relay1": 26,  # HEAT pin, Board 37
    "Relay2": 20,  # COOL pin, Board 38
    "Relay3": 21,  # AUX/Fan pin, Board 40
}


class RelayControl:
    def __init__(self, settings_manager):
        self.settings = settings_manager
        self.gpio = GPIO
        self.pins = [RELAY_PINS["Relay1"], RELAY_PINS["Relay2"], RELAY_PINS["Relay3"]]
        self.relay_state_cache = [False, False, False]
        self.manual_override = [None, None, None]  # None=auto, True=on, False=off
        self.logger = None
        self._update_relay_logic()
        self._setup_gpio()

    def _update_relay_logic(self):
        active_high = self.settings.get("relay_active_high", False)
        if active_high:
            self.RELAY_ON = self.gpio.HIGH
            self.RELAY_OFF = self.gpio.LOW
        else:
            self.RELAY_ON = self.gpio.LOW
            self.RELAY_OFF = self.gpio.HIGH

    def set_logger(self, logger_callable):
        self.logger = logger_callable

    def _setup_gpio(self):
        self.gpio.setwarnings(False)
        for pin in self.pins:
            try:
                pin_int = int(pin)
                self.gpio.setup(pin_int, self.gpio.OUT)
                self.gpio.output(pin_int, self.RELAY_OFF)
            except Exception as e:
                print(f"[RelayControl] GPIO setup error for pin {pin}: {e}")

    def set_relay_states(self, desired_states):
        """
        desired_states: list of 3 booleans [r0, r1, r2]
        Respects manual overrides: if manual_override[i] is not None, use that instead.
        """
        self._update_relay_logic()
        for i, pin in enumerate(self.pins):
            if self.manual_override[i] is not None:
                state = self.manual_override[i]
            else:
                state = desired_states[i] if i < len(desired_states) else False
            try:
                self.gpio.output(int(pin), self.RELAY_ON if state else self.RELAY_OFF)
                self.relay_state_cache[i] = state
            except Exception as e:
                print(f"[RelayControl] Error setting relay {i}: {e}")

    def set_relay_states_direct(self, desired_states):
        """Apply states directly without checking manual_override (mode logic handled by App)."""
        self._update_relay_logic()
        for i, pin in enumerate(self.pins):
            state = desired_states[i] if i < len(desired_states) else False
            try:
                self.gpio.output(int(pin), self.RELAY_ON if state else self.RELAY_OFF)
                self.relay_state_cache[i] = state
            except Exception as e:
                print(f"[RelayControl] Error setting relay {i}: {e}")

    def set_manual_override(self, relay_idx, on_off):
        """
        on_off: True=force ON, False=force OFF, None=auto (follow schedule/thermo)
        """
        if 0 <= relay_idx < 3:
            self.manual_override[relay_idx] = on_off
            if self.logger:
                label = self.settings.get_relay_config(relay_idx).get("label", f"Relay {relay_idx+1}")
                if on_off is None:
                    self.logger(f"Manual override cleared for {label}.")
                else:
                    self.logger(f"Manual override: {label} -> {'ON' if on_off else 'OFF'}")

    def clear_all_manual_overrides(self):
        self.manual_override = [None, None, None]
        if self.logger:
            self.logger("All manual overrides cleared.")

    def is_relay_on(self, relay_idx):
        if 0 <= relay_idx < 3:
            return self.relay_state_cache[relay_idx]
        return False

    def cleanup_gpio(self):
        try:
            for pin in self.pins:
                self.gpio.output(int(pin), self.RELAY_OFF)
            self.gpio.cleanup()
            print("[RelayControl] GPIO cleanup complete.")
        except Exception as e:
            print(f"[RelayControl] Cleanup error: {e}")
