#!/usr/bin/env bash
#
# First-time setup for the surveillance camera app on a Raspberry Pi.
#
#   1. Installs system packages (ffmpeg, Picamera2, Node.js/npm, python venv)
#   2. Creates/updates the Python virtualenv and installs backend requirements
#   3. Builds the React frontend (served by Flask on port 5000)
#   4. Creates backend/.env with a random SECRET_KEY if it doesn't exist
#   5. Installs and starts the systemd service (replacing old services)
#
# Run as the normal user (NOT with sudo); it calls sudo itself when needed:
#   ./install.sh
#
# Options:
#   --venv PATH     Python virtualenv to use/create   (default: ~/my-venv)
#   --skip-deps     Skip apt and pip installs
#   --skip-build    Skip the frontend build (e.g. you copied frontend/build from a PC)
#   --uninstall     Stop and remove the systemd service
#   -h, --help      Show this help
#
# Safe to re-run: use it after `git pull` to rebuild and restart.

set -euo pipefail

SERVICE_NAME="surveillance-backend"
OLD_SERVICES=("myapp" "surveillance-frontend")
PORT=5000

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
VENV="$HOME/my-venv"
SKIP_DEPS=0
SKIP_BUILD=0
UNINSTALL=0

info()  { echo -e "\033[1;32m==>\033[0m $*"; }
warn()  { echo -e "\033[1;33m[!]\033[0m $*"; }
fail()  { echo -e "\033[1;31m[x]\033[0m $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv)       VENV="$2"; shift 2 ;;
        --skip-deps)  SKIP_DEPS=1; shift ;;
        --skip-build) SKIP_BUILD=1; shift ;;
        --uninstall)  UNINSTALL=1; shift ;;
        -h|--help)    sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)            fail "Unknown option: $1 (see --help)" ;;
    esac
done

[[ $EUID -eq 0 ]] && fail "Run as your normal user, not root/sudo. The script uses sudo where needed."
[[ -f "$BACKEND_DIR/app.py" ]] || fail "backend/app.py not found in $APP_DIR"

APP_USER="$(id -un)"
UNIT_FILE="/etc/systemd/system/$SERVICE_NAME.service"

# ---------------------------------------------------------------- uninstall
if [[ $UNINSTALL -eq 1 ]]; then
    info "Removing $SERVICE_NAME service"
    sudo systemctl disable --now "$SERVICE_NAME" 2>/dev/null || true
    sudo rm -f "$UNIT_FILE"
    sudo systemctl daemon-reload
    info "Done. App files, venv and recordings were left untouched."
    exit 0
fi

sudo -v || fail "sudo is required"

# ---------------------------------------------------------------- 1. system packages
if [[ $SKIP_DEPS -eq 0 ]]; then
    info "Installing system packages"
    PKGS=(ffmpeg python3-venv python3-pip curl)
    # Pi camera module (ribbon cable) needs Picamera2 from apt; it is not pip-installable.
    if apt-cache show python3-picamera2 >/dev/null 2>&1; then
        PKGS+=(python3-picamera2)
    else
        warn "python3-picamera2 not available from apt: only a USB webcam will work"
    fi
    command -v npm >/dev/null 2>&1 || PKGS+=(nodejs npm)
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${PKGS[@]}"
fi

# Camera access
if ! id -nG "$APP_USER" | grep -qw video; then
    info "Adding $APP_USER to the 'video' group (camera access)"
    sudo usermod -aG video "$APP_USER"
fi

# ---------------------------------------------------------------- 2. python venv
if [[ ! -x "$VENV/bin/python" ]]; then
    info "Creating virtualenv at $VENV"
    # --system-site-packages so the apt-installed Picamera2 is visible
    python3 -m venv --system-site-packages "$VENV"
elif ! grep -q "include-system-site-packages = true" "$VENV/pyvenv.cfg" 2>/dev/null; then
    warn "$VENV was created without --system-site-packages; Picamera2 may not be importable."
    warn "If the Pi camera isn't detected, recreate it: rm -rf $VENV && ./install.sh"
fi
PYTHON="$VENV/bin/python"

if [[ $SKIP_DEPS -eq 0 ]]; then
    info "Installing Python requirements (can take a while on a Pi 3B)"
    "$PYTHON" -m pip install --upgrade pip -q
    "$PYTHON" -m pip install -q -r "$BACKEND_DIR/requirements.txt"
    # The app forces threading mode; a stray gevent install is not needed.
    if "$PYTHON" -c "import gevent" 2>/dev/null; then
        warn "gevent is installed in the venv but unused (app runs in threading mode)"
    fi
fi

CAMERA_KIND="$(cd "$BACKEND_DIR" && "$PYTHON" -c 'import config; print("Pi camera (Picamera2)" if config.USE_PICAMERA else "USB webcam (OpenCV)")' 2>/dev/null || echo "unknown (config import failed)")"
info "Camera source detected: $CAMERA_KIND"

# ---------------------------------------------------------------- 3. frontend build
if [[ $SKIP_BUILD -eq 0 ]]; then
    info "Building frontend"
    if [[ -f "$FRONTEND_DIR/.env" ]] && grep -q "^REACT_APP_API_BASE_URL" "$FRONTEND_DIR/.env"; then
        warn "frontend/.env sets REACT_APP_API_BASE_URL; the build will call that address"
        warn "instead of the address the page is opened from. Remove it unless you need it."
    fi
    command -v node >/dev/null 2>&1 || fail "Node.js not found (install it or use --skip-build)"
    NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
    if [[ "$NODE_MAJOR" -lt 16 ]]; then
        fail "Node.js $(node -v) is too old for react-scripts 5 (need 16+). Install a newer Node
    (e.g. from https://deb.nodesource.com) or build on a PC and use --skip-build"
    fi
    cd "$FRONTEND_DIR"
    if [[ ! -d node_modules ]]; then
        if [[ -f package-lock.json ]]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi
    fi
    # No source maps: much less memory (the Pi 3B has only 1 GB)
    GENERATE_SOURCEMAP=false npm run build \
        || fail "Frontend build failed. On a Pi 3B this is usually out-of-memory: increase swap
    (sudo dphys-swapfile swapoff; set CONF_SWAPSIZE=1024 in /etc/dphys-swapfile;
     sudo dphys-swapfile setup; sudo dphys-swapfile swapon) or build on a PC and copy
    frontend/build to the Pi, then run ./install.sh --skip-build"
    cd "$APP_DIR"
elif [[ ! -f "$FRONTEND_DIR/build/index.html" ]]; then
    warn "--skip-build given but frontend/build/index.html doesn't exist"
fi

# ---------------------------------------------------------------- 4. backend .env
if [[ ! -f "$BACKEND_DIR/.env" ]]; then
    info "Creating backend/.env"
    SECRET="$("$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(24))')"
    cat > "$BACKEND_DIR/.env" <<EOF
# Used to sign sessions, and as the registration code for new users
SECRET_KEY=$SECRET
# Optional: public IP or DNS name used to reach the camera from outside your network
#EXTERNAL_IP=
# Optional: Gmail account for registration emails
#MAIL_USERNAME=
#MAIL_PASSKEY=
EOF
    chmod 600 "$BACKEND_DIR/.env"
    warn "Registration code for new users (SECRET_KEY in backend/.env): $SECRET"
fi

# ---------------------------------------------------------------- 5. systemd service
for old in "${OLD_SERVICES[@]}"; do
    if systemctl list-unit-files "$old.service" 2>/dev/null | grep -q "^$old.service"; then
        info "Disabling old service: $old"
        sudo systemctl disable --now "$old" 2>/dev/null || true
    fi
done

info "Installing $UNIT_FILE"
sudo tee "$UNIT_FILE" >/dev/null <<EOF
[Unit]
Description=Surveillance camera (Flask backend + React frontend on port $PORT)
After=network-online.target
Wants=network-online.target

[Service]
User=$APP_USER
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=-$BACKEND_DIR/.env
Environment=PYTHONUNBUFFERED=1
ExecStart=$PYTHON -u app.py
Restart=always
RestartSec=5
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME" >/dev/null
info "Starting $SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# ---------------------------------------------------------------- check
info "Waiting for the server on port $PORT"
for _ in $(seq 1 30); do
    if curl -fs "http://localhost:$PORT/ping" >/dev/null 2>&1; then
        LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
        echo
        info "Running! Open http://${LAN_IP:-<pi-ip>}:$PORT"
        echo "    Logs:     journalctl -u $SERVICE_NAME -f"
        echo "    Restart:  sudo systemctl restart $SERVICE_NAME"
        echo "    Update:   git pull && ./install.sh --skip-deps"
        exit 0
    fi
    sleep 2
done

warn "Server did not respond on port $PORT within 60s. Recent logs:"
sudo journalctl -u "$SERVICE_NAME" -n 30 --no-pager
exit 1
