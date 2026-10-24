"""Push-to-talk: hold a key on the right of the keyboard, anywhere on the computer."""

import logging
import sys

log = logging.getLogger("happy.keys")

MAC_KEYS = {"right_option": (61, 0x40), "right_command": (54, 0x10), "right_ctrl": (62, 0x2000),
            "right_shift": (60, 0x04), "fn": (63, 0x800000)}


class PushToTalk:
    def __init__(self, key, on_down, on_up, note=None, on_cancel=None):
        self.key = key or ("right_option" if sys.platform == "darwin" else "right_ctrl")
        self.on_down = on_down
        self.on_up = on_up
        self.note = note or (lambda text: None)
        self.on_cancel = on_cancel or on_up
        self.held = False
        self.combo = False
        self.monitors = []
        self.listener = None

    def start(self):
        try:
            self.start_mac() if sys.platform == "darwin" else self.start_other()
        except Exception:
            log.exception("push-to-talk is not available")

    def start_mac(self):
        from AppKit import NSEvent, NSEventMaskFlagsChanged, NSEventMaskKeyDown
        from ApplicationServices import AXIsProcessTrustedWithOptions

        if not AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True}):
            self.note("To hold a key to talk, allow Accessibility for this terminal in System Settings, then restart Happy.")
        code, mask = MAC_KEYS.get(self.key, MAC_KEYS["right_option"])

        def changed(event):
            if event.type() == 10:
                if self.held:
                    self.combo = True
                return
            if event.keyCode() != code:
                return
            down = bool(event.modifierFlags() & mask)
            if down and not self.held:
                self.held, self.combo = True, False
                self.on_down()
            elif not down and self.held:
                self.held = False
                self.on_cancel() if self.combo else self.on_up()

        events = NSEventMaskFlagsChanged | NSEventMaskKeyDown
        self.monitors.append(NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(events, changed))
        self.monitors.append(NSEvent.addLocalMonitorForEventsMatchingMask_handler_(events, lambda e: (changed(e), e)[1]))

    def start_other(self):
        from pynput import keyboard

        wanted = {"right_ctrl": keyboard.Key.ctrl_r, "right_option": keyboard.Key.alt_r, "right_alt": keyboard.Key.alt_r,
                  "right_shift": keyboard.Key.shift_r, "right_command": keyboard.Key.cmd_r}.get(self.key, keyboard.Key.ctrl_r)

        def pressed(key):
            if key == wanted and not self.held:
                self.held = True
                self.on_down()

        def released(key):
            if key == wanted and self.held:
                self.held = False
                self.on_up()

        self.listener = keyboard.Listener(on_press=pressed, on_release=released)
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
        if self.monitors:
            from AppKit import NSEvent

            for monitor in self.monitors:
                if monitor is not None:
                    NSEvent.removeMonitor_(monitor)
