from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


HOST = "0.0.0.0"
PORT = int(os.environ.get("OUMAX_MANUAL_PORT", "8765"))
UDP_PORT = int(os.environ.get("OUMAX_GAMEPAD_UDP_PORT", str(PORT + 1)))
UDP_WATCHDOG_SEC = float(os.environ.get("OUMAX_GAMEPAD_WATCHDOG_SEC", "0.35"))
SERIAL_PORT = os.environ.get("OUMAX_SERIAL_PORT", "/dev/ttyAMA0")
DOG_VERSION = os.environ.get("OUMAX_DOG_VERSION", "auto")

dog = None
dog_lock = threading.RLock()
udp_last_seen = 0.0
udp_last_active = False
udp_latest_payload = None
udp_payload_lock = threading.Lock()
udp_payload_event = threading.Event()


def get_dog():
    global dog
    if dog is None:
        from xgolib import XGO

        dog = XGO(port=SERIAL_PORT, version=xgo_constructor_version(DOG_VERSION))
    return dog


def xgo_constructor_version(version: str) -> str:
    normalized = str(version or "auto").lower()
    if normalized in {"xgomini2sw", "mini2sw", "xgomini3w", "mini3w"}:
        return "xgomini"
    return version


_motion_timers: dict[str, threading.Timer] = {}


def _cancel_motion_timers() -> None:
    for timer in _motion_timers.values():
        timer.cancel()
    _motion_timers.clear()


def _kick_axis(axis: str, runtime: float) -> None:
    """Watchdog-style motion: a fresh command re-arms the stop timer, so the
    physical action continues only while commands keep arriving."""
    previous = _motion_timers.pop(axis, None)
    if previous is not None:
        previous.cancel()
    if runtime <= 0:
        return

    def _do_stop() -> None:
        try:
            bot = get_dog()
            if axis == "x":
                bot.move_x(0, 0)
            elif axis == "y":
                bot.move_y(0, 0)
            else:
                bot.turn(0, 0)
        except Exception as exc:  # serial hiccup: do not crash the service
            print(f"motion stop failed: {exc}", flush=True)

    timer = threading.Timer(runtime, _do_stop)
    timer.daemon = True
    _motion_timers[axis] = timer
    timer.start()


def handle_motion(payload: dict[str, Any]) -> str:
    bot = get_dog()
    axis = payload.get("axis", "stop")
    value = float(payload.get("value", 0))
    runtime = float(payload.get("runtime", 0) or 0)
    mode = payload.get("drive_mode", "auto")

    if axis == "stop":
        _cancel_motion_timers()
        stop_bot(bot, mode)
    elif mode == "wheel4" and is_wheel_dog(bot):
        handle_wheel({"enabled": True, "speeds": wheel_speeds(axis, value)})
    elif axis == "x":
        bot.move_x(value, 0)
        _kick_axis("x", runtime)
    elif axis == "y":
        bot.move_y(value, 0)
        _kick_axis("y", runtime)
    elif axis == "yaw":
        bot.turn(value, 0)
        _kick_axis("yaw", runtime)
    else:
        raise ValueError(f"unknown motion axis: {axis}")
    return f"motion {axis}={value} mode={mode}"


def wheel_speeds(axis: str, value: float) -> list[float]:
    speed = max(-1.2, min(1.2, value / 30.0))
    if axis == "x":
        return [speed, speed, speed, speed]
    if axis == "y":
        return [-speed, speed, speed, -speed]
    if axis == "yaw":
        return [-speed, speed, -speed, speed]
    raise ValueError(f"unknown wheel motion axis: {axis}")


def handle_arm(payload: dict[str, Any]) -> str:
    bot = get_dog()
    command = payload.get("command", "cartesian")

    if command == "cartesian":
        bot.arm(float(payload.get("x", 80)), float(payload.get("z", 60)))
    elif command == "polar":
        bot.arm_polar(float(payload.get("theta", 90)), float(payload.get("radius", 80)))
    elif command == "claw":
        bot.claw(int(payload.get("claw", 128)))
    elif command == "motor" and hasattr(bot, "arm_motor"):
        bot.arm_motor(payload.get("angles", [0, 0, 0]))
    elif command == "rotate" and hasattr(bot, "arm_rotate"):
        bot.arm_rotate(float(payload.get("theta", 0)))
    elif command == "mid" and hasattr(bot, "moveToMid"):
        bot.moveToMid()
    else:
        raise ValueError(f"unknown arm command: {command}")
    return f"arm {command}"


MOTOR_RANGES: dict[int, tuple[float, float]] = {
    11: (-73, 57), 12: (-66, 93), 13: (-31, 31),
    21: (-73, 57), 22: (-66, 93), 23: (-31, 31),
    31: (-73, 57), 32: (-66, 93), 33: (-31, 31),
    41: (-73, 57), 42: (-66, 93), 43: (-31, 31),
    51: (-65, 65), 52: (-115, 70), 53: (-85, 100),
}


def handle_motor(payload: dict[str, Any]) -> str:
    bot = get_dog()
    try:
        motor_id = int(payload.get("id"))
        angle = float(payload.get("angle"))
    except (TypeError, ValueError):
        raise ValueError(f"电机 id 或角度无效: id={payload.get('id')!r} angle={payload.get('angle')!r}")
    bounds = MOTOR_RANGES.get(motor_id)
    if bounds is None:
        raise ValueError(f"未知电机 id: {motor_id}")
    low, high = bounds
    if not low <= angle <= high:
        raise ValueError(f"电机 {motor_id} 角度 {angle} 超出范围 [{low}, {high}]")
    bot.motor(motor_id, angle)
    return f"motor {motor_id}={angle:g}"


def handle_wheel(payload: dict[str, Any]) -> str:
    bot = get_dog()
    enabled = payload.get("enabled")
    speeds = payload.get("speeds") or [0, 0, 0, 0]

    if not is_wheel_dog(bot):
        raise ValueError("wheel mode is unavailable on this foot-type dog")
    if enabled is not None and hasattr(bot, "enable_wheel_control"):
        bot.enable_wheel_control(1 if enabled else 0)
    send_wheel_control(bot, speeds)
    return f"wheel speeds={speeds}"


def handle_gamepad(payload: dict[str, Any]) -> str:
    bot = get_dog()
    x = clamp(float(payload.get("x", 0)), -1, 1)
    y = clamp(float(payload.get("y", 0)), -1, 1)
    yaw = clamp(float(payload.get("yaw", 0)), -1, 1)
    requested_mode = str(payload.get("drive_mode", "dog") or "dog")
    mode = "wheel4" if requested_mode == "wheel4" and is_wheel_dog(bot) else "dog"

    if abs(x) < 0.05 and abs(y) < 0.05 and abs(yaw) < 0.05:
        stop_bot(bot, requested_mode)
        return f"gamepad stop mode={mode}"

    if mode == "wheel4":
        if hasattr(bot, "enable_wheel_control"):
            bot.enable_wheel_control(1)
        send_wheel_control(bot, gamepad_wheel_speeds(x, y, yaw))
    else:
        send_foot_control(bot, x, y, yaw)
    return f"gamepad x={x:.2f} y={y:.2f} yaw={yaw:.2f} mode={mode}"


def send_foot_control(bot: Any, x: float, y: float, yaw: float) -> None:
    bot.move_x(round(x * 25, 2))
    bot.move_y(round(y * 18, 2))
    bot.turn(round(yaw * 80, 2))


def stop_bot(bot: Any, requested_mode: str = "") -> None:
    bot.stop()
    if requested_mode == "wheel4" and is_wheel_dog(bot):
        send_wheel_control(bot, [0, 0, 0, 0])


def is_wheel_dog(bot: Any) -> bool:
    version = str(getattr(bot, "version", "") or "").lower()
    configured = str(DOG_VERSION or "").lower()
    return (
        version.startswith("w")
        or "mini3w" in configured
        or "mini2sw" in configured
        or hasattr(bot, "wheel_control")
    )


def gamepad_wheel_speeds(x: float, y: float, yaw: float) -> list[float]:
    # This unit has only the LEFT pair (lf, lr) driven; rf/rr are free-spinning
    # brushless passives. Rotate by running lf vs lr in opposition.
    lf = x - yaw
    lr = x + yaw
    values = [lf, 0.0, lr, 0.0]
    peak = max(1.0, max(abs(v) for v in values))
    return [round(v / peak * 1.15, 3) for v in values]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def send_wheel_control(bot: Any, speeds: list[float]) -> None:
    values = [float(v) for v in list(speeds)[:4]]
    values += [0.0] * (4 - len(values))
    if hasattr(bot, "wheel_control"):
        bot.wheel_control([wheel_byte(v) for v in values])
        return
    if hasattr(bot, "wheel_speed"):
        try:
            bot.wheel_speed(values)
        except TypeError:
            for index, value in enumerate(values, start=1):
                bot.wheel_speed(index, value)
        return
    raise ValueError("wheel control is not available on this dog version")


def wheel_byte(speed: float) -> int:
    value = max(-1.5, min(1.5, speed))
    return max(0, min(255, int(round(128 + value / 1.5 * 127))))


def handle_speak(payload: dict[str, Any]) -> str:
    text = str(payload.get("text") or "").strip()
    if not text:
        raise ValueError("speak text is empty")

    commands = [
        ("espeak-ng", ["espeak-ng", "-v", "zh", "-s", "150", text]),
        ("espeak", ["espeak", "-v", "zh", "-s", "150", text]),
        ("spd-say", ["spd-say", text]),
        ("flite", ["flite", "-t", text]),
    ]
    for binary, command in commands:
        if shutil.which(binary):
            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"speak on dog: {text}"
    raise RuntimeError("no TTS command found on CM5; install espeak-ng or another TTS tool")


def dispatch(payload: dict[str, Any]) -> dict[str, Any]:
    with dog_lock:
        kind = payload.get("kind")
        if kind == "motion":
            message = handle_motion(payload)
        elif kind == "arm":
            message = handle_arm(payload)
        elif kind == "motor":
            message = handle_motor(payload)
        elif kind == "wheel":
            message = handle_wheel(payload)
        elif kind == "gamepad":
            message = handle_gamepad(payload)
        elif kind == "speak":
            message = handle_speak(payload)
        elif kind in {"ping", "health"}:
            message = "pong"
        else:
            raise ValueError(f"unknown command kind: {kind}")
    return {"ok": True, "mode": "manual-runtime", "message": message}


def is_active_gamepad_payload(payload: dict[str, Any]) -> bool:
    if payload.get("kind") == "motion":
        return payload.get("axis") != "stop" and abs(float(payload.get("value", 0))) >= 0.01
    if payload.get("kind") != "gamepad":
        return False
    x = abs(float(payload.get("x", 0)))
    y = abs(float(payload.get("y", 0)))
    yaw = abs(float(payload.get("yaw", 0)))
    return x >= 0.05 or y >= 0.05 or yaw >= 0.05


def mark_udp_seen(payload: dict[str, Any]) -> None:
    global udp_last_seen, udp_last_active
    if payload.get("kind") not in {"gamepad", "motion"}:
        return
    udp_last_seen = time.monotonic()
    udp_last_active = is_active_gamepad_payload(payload)


def stop_from_watchdog() -> None:
    global udp_last_active
    try:
        dispatch({"kind": "gamepad", "x": 0, "y": 0, "yaw": 0, "drive_mode": "dog", "name": "udp-watchdog"})
        print("udp watchdog stop", flush=True)
    except Exception as exc:
        print(f"udp watchdog stop failed: {exc}", flush=True)
    finally:
        udp_last_active = False


def udp_watchdog_loop() -> None:
    while True:
        time.sleep(0.05)
        if udp_last_active and time.monotonic() - udp_last_seen > UDP_WATCHDOG_SEC:
            stop_from_watchdog()


def udp_server_loop() -> None:
    global udp_latest_payload
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, UDP_PORT))
    print(f"gamepad udp server listening on {HOST}:{UDP_PORT}", flush=True)
    while True:
        data, address = sock.recvfrom(4096)
        try:
            payload = json.loads(data.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("udp payload must be a json object")
            mark_udp_seen(payload)
            with udp_payload_lock:
                udp_latest_payload = payload
                udp_payload_event.set()
            result = {"ok": True, "mode": "manual-runtime", "message": "queued latest gamepad frame"}
        except Exception as exc:
            result = {"ok": False, "mode": "manual-runtime", "message": str(exc)}
        try:
            sock.sendto(json.dumps(result, ensure_ascii=False).encode("utf-8"), address)
        except OSError as exc:
            print(f"udp response failed: {exc}", flush=True)


def udp_dispatch_loop() -> None:
    global udp_latest_payload
    while True:
        udp_payload_event.wait()
        while True:
            with udp_payload_lock:
                payload = udp_latest_payload
                udp_latest_payload = None
                if payload is None:
                    udp_payload_event.clear()
                    break
            try:
                dispatch(payload)
            except Exception as exc:
                print(f"udp dispatch failed: {exc}", flush=True)


def read_imu_angles() -> dict[str, float]:
    """Read body attitude from the dog's on-board IMU (degrees)."""
    bot = get_dog()
    yaw = bot.read_yaw() if hasattr(bot, "read_yaw") else 0.0
    pitch = bot.read_pitch() if hasattr(bot, "read_pitch") else 0.0
    roll = bot.read_roll() if hasattr(bot, "read_roll") else 0.0
    return {"yaw": yaw, "pitch": pitch, "roll": roll}


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/health":
            self.respond(
                {
                    "ok": True,
                    "dog_version": DOG_VERSION,
                    "serial_port": SERIAL_PORT,
                    "manual_port": PORT,
                    "gamepad_udp_port": UDP_PORT,
                }
            )
            return
        if self.path == "/imu":
            try:
                with dog_lock:
                    angles = read_imu_angles()
                self.respond({"ok": True, **angles})
            except Exception as exc:
                self.respond({"ok": False, "message": str(exc)}, status=500)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/command":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self.respond(dispatch(payload))
        except Exception as exc:
            self.respond({"ok": False, "message": str(exc)}, status=500)

    def log_message(self, fmt: str, *args: object) -> None:
        print(fmt % args, flush=True)

    def respond(self, data: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    threading.Thread(target=udp_server_loop, name="gamepad-udp", daemon=True).start()
    threading.Thread(target=udp_dispatch_loop, name="gamepad-dispatch", daemon=True).start()
    threading.Thread(target=udp_watchdog_loop, name="gamepad-watchdog", daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"manual control server listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()
