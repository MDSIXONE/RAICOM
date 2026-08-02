#!/usr/bin/env python3
from __future__ import annotations

import os
import socket
import threading
import time
from typing import Optional

import serial

HOST = "0.0.0.0"
PORT = int(os.environ.get("OUMAX_RAW_XGO_PORT", "8765"))
SERIAL_PORT = os.environ.get("OUMAX_SERIAL_PORT", "/dev/ttyAMA0")
BAUD = int(os.environ.get("OUMAX_SERIAL_BAUD", "115200"))
WATCHDOG_SEC = float(os.environ.get("OUMAX_RAW_XGO_WATCHDOG_SEC", "0.45"))

# Quadruped XGO registers used by the current MAXVR APK bridge. Wheel-foot
# registers are intentionally not accepted on this four-foot dog.
ALLOWED_REGISTERS = {
    0x09,                    # gait
    0x30, 0x31, 0x32,        # velocity x/y/yaw
    0x33, 0x34, 0x35,        # body x/y/height
    0x36, 0x37, 0x38,        # roll/pitch/yaw
    0x39, 0x3A, 0x3B,        # rotate periods
    0x3C, 0x3D, 0x3E, 0x3F, # step/mode/action/rotate angle
    0x50,                    # motor angle
    0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77,
}
MOTION_REGISTERS = {0x30, 0x31, 0x32}
STOP_FRAMES = bytes.fromhex("55 00 09 00 30 80 46 00 aa") + \
              bytes.fromhex("55 00 09 00 31 80 45 00 aa") + \
              bytes.fromhex("55 00 09 00 32 80 44 00 aa")

ser_lock = threading.RLock()
ser: Optional[serial.Serial] = None
last_motion_time = 0.0
motion_active = False


def open_serial() -> serial.Serial:
    global ser
    with ser_lock:
        if ser is not None and ser.is_open:
            return ser
        ser = serial.Serial(SERIAL_PORT, BAUD, timeout=0.1, write_timeout=0.2)
        print(f"opened serial {SERIAL_PORT} @ {BAUD}", flush=True)
        return ser


def checksum(frame: bytes) -> int:
    length = frame[2]
    data_len = length - 0x08
    data_sum = sum(frame[5:5 + data_len])
    return 255 - ((length + frame[3] + frame[4] + data_sum) % 256)


def normalize_frame(frame: bytes) -> Optional[bytes]:
    if len(frame) < 9:
        return None
    length = frame[2]
    if length != len(frame) or length < 9:
        return None
    if frame[0] != 0x55 or frame[1] != 0x00 or frame[-2] != 0x00 or frame[-1] != 0xAA:
        return None
    mode = frame[3]
    addr = frame[4]
    if mode not in (0x00, 0x01):
        return None
    if addr not in ALLOWED_REGISTERS:
        return None

    out = bytearray(frame)
    out[3] = 0x00
    out[-3] = checksum(out)
    if out[-3] != frame[-3] and mode == 0x00:
        # Accept old checksum mismatch only after normalizing mode 0x01. For
        # normal mode 0x00, reject corrupt TCP stream data.
        return None
    return bytes(out)


def write_frame(frame: bytes) -> None:
    global last_motion_time, motion_active
    bot = open_serial()
    with ser_lock:
        bot.write(frame)
        bot.flush()
    addr = frame[4]
    if addr in MOTION_REGISTERS:
        last_motion_time = time.monotonic()
        if len(frame) >= 9 and frame[5] != 0x80:
            motion_active = True
        elif all_stop_frame(frame):
            motion_active = False


def all_stop_frame(frame: bytes) -> bool:
    return frame[4] in MOTION_REGISTERS and len(frame) >= 9 and frame[5] == 0x80


def send_stop() -> None:
    global motion_active
    try:
        bot = open_serial()
        with ser_lock:
            bot.write(STOP_FRAMES)
            bot.flush()
        print("watchdog/disconnect stop sent", flush=True)
    except Exception as exc:
        print(f"stop failed: {exc}", flush=True)
    motion_active = False


def watchdog_loop() -> None:
    global motion_active
    while True:
        time.sleep(0.05)
        if motion_active and time.monotonic() - last_motion_time > WATCHDOG_SEC:
            send_stop()


def handle_client(conn: socket.socket, addr) -> None:
    print(f"client connected {addr}", flush=True)
    buf = bytearray()
    forwarded = 0
    rejected = 0
    try:
        conn.settimeout(1.0)
        while True:
            try:
                data = conn.recv(4096)
            except socket.timeout:
                continue
            if not data:
                break
            buf.extend(data)
            while True:
                header = buf.find(b"\x55\x00")
                if header < 0:
                    if len(buf) > 1:
                        del buf[:-1]
                    break
                if header > 0:
                    del buf[:header]
                if len(buf) < 3:
                    break
                length = buf[2]
                if length < 9 or length > 64:
                    del buf[0]
                    rejected += 1
                    continue
                if len(buf) < length:
                    break
                candidate = bytes(buf[:length])
                del buf[:length]
                frame = normalize_frame(candidate)
                if frame is None:
                    rejected += 1
                    continue
                write_frame(frame)
                forwarded += 1
    except Exception as exc:
        print(f"client {addr} error: {exc}", flush=True)
    finally:
        try:
            conn.close()
        except Exception:
            pass
        send_stop()
        print(f"client disconnected {addr}, forwarded={forwarded}, rejected={rejected}", flush=True)


def main() -> None:
    open_serial()
    send_stop()
    threading.Thread(target=watchdog_loop, name="raw-xgo-watchdog", daemon=True).start()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(8)
    print(f"raw XGO TCP server listening on {HOST}:{PORT} -> {SERIAL_PORT}", flush=True)
    while True:
        conn, addr = sock.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
