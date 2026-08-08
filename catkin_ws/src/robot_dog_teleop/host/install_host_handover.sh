#!/usr/bin/env bash
# Install the host-side ownership handover.  Default is install-only; --cutover
# is explicit because it stops and restarts the original on-device UI once.
set -euo pipefail

MODE="${1:---install-only}"
if [[ "$MODE" != "--install-only" && "$MODE" != "--cutover" ]]; then
  echo "Usage: sudo $0 [--install-only|--cutover]" >&2
  exit 64
fi
[[ "${EUID}" -eq 0 ]] || { echo "Run as root with sudo." >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RC_LOCAL="/etc/rc.local"
RC_BACKUP="/etc/rc.local.raicom-pre-handover"
LEGACY_LINE='su - pi -c "cd /home/pi/RaspberryPi-CM5 && source xgovenv/bin/activate && exec python common/main.py >> /home/pi/app.log 2>&1"'
MARKER='# RAICOM: original main is managed by raicom-original-main.service.'

test -f "$RC_LOCAL"
install -m 0755 "$SCRIPT_DIR/raicom-control-handover" /usr/local/sbin/raicom-control-handover
install -m 0755 "$SCRIPT_DIR/launch_physical_keyboard_teleop.sh" /usr/local/sbin/raicom-launch-physical-keyboard
install -m 0755 "$SCRIPT_DIR/launch_physical_keyboard_continuous.sh" /usr/local/sbin/raicom-launch-physical-keyboard-continuous
install -m 0755 "$SCRIPT_DIR/launch_pose_keyboard_teleop.sh" /usr/local/sbin/raicom-launch-pose-keyboard
install -m 0644 "$SCRIPT_DIR/raicom-original-main.service" /etc/systemd/system/raicom-original-main.service

if ! grep -Fqx "$MARKER" "$RC_LOCAL"; then
  grep -Fqx "$LEGACY_LINE" "$RC_LOCAL" || {
    echo "Refusing to modify unexpected rc.local; no changes were made to its main-app line." >&2
    exit 3
  }
  test -e "$RC_BACKUP" || cp -p "$RC_LOCAL" "$RC_BACKUP"
  perl -0pi -e 's{^su - pi -c "cd /home/pi/RaspberryPi-CM5 && source xgovenv/bin/activate && exec python common/main.py >> /home/pi/app.log 2>&1"$}{# RAICOM: original main is managed by raicom-original-main.service.}m' "$RC_LOCAL"
fi

systemctl daemon-reload
systemctl enable raicom-original-main.service

if [[ "$MODE" == "--install-only" ]]; then
  echo "Installed only. Original app runtime was not changed. Later, after charging and on-site confirmation, run this same script with --cutover."
  exit 0
fi

# The cutover is recoverable: manual service is disabled at boot, the legacy
# rc.local launch has been replaced by the managed service, and the existing
# original process is replaced once by its systemd-managed equivalent.
systemctl disable oumax-manual.service
systemctl stop oumax-manual.service || true
pkill -TERM -f '^python common/main.py$' || true
for attempt in $(seq 1 25); do
  if ! fuser /dev/ttyAMA0 >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done
if fuser /dev/ttyAMA0 >/dev/null 2>&1; then
  echo "Legacy app did not release ttyAMA0; restoring boot configuration and refusing cutover." >&2
  cp -p "$RC_BACKUP" "$RC_LOCAL"
  systemctl daemon-reload
  exit 4
fi
if ! systemctl start raicom-original-main.service || ! systemctl is-active --quiet raicom-original-main.service; then
  echo "Managed original app did not start; restoring rc.local and leaving manual control stopped." >&2
  systemctl stop raicom-original-main.service || true
  cp -p "$RC_BACKUP" "$RC_LOCAL"
  systemctl daemon-reload
  exit 5
fi
echo "Cutover complete. The original app is now managed and can be safely handed over by raicom-control-handover."
