#!/bin/bash

echo "===== Surveillance App Installer ====="

# Get current project path
PROJECT_PATH="$(pwd)"
USER_NAME="$(whoami)"
HOME_DIR="$HOME"

BACKEND_SERVICE_FILE="/etc/systemd/system/surveillance_backend.service"
FRONTEND_SERVICE_FILE="/etc/systemd/system/surveillance_frontend.service"

echo "Project path detected: $PROJECT_PATH"
echo "User detected: $USER_NAME"
read -p "[1/3] Is user name correct? (y/n): " USER_OK
if [[ "$USER_OK" == "y" || "$USER_OK" == "Y" ]]; then
    echo ""
else
    exit 1
fi
# Ask user about virtual environment
read -p "[2/3] Do you want to use a virtual environment? (y/n): " USE_VENV

if [[ "$USE_VENV" == "y" || "$USE_VENV" == "Y" ]]; then
    read -p "Enter full path to your venv (example: /home/$USER_NAME/my-venv): " VENV_PATH
    PYTHON_CMD="$VENV_PATH/bin/python"
    VENV_SOURCE="source $VENV_PATH/bin/activate"
    VENV_PATH_EXPORT="$VENV_PATH/bin"
else
    PYTHON_CMD="python3"
    VENV_SOURCE=""
    VENV_PATH_EXPORT=""
fi

# Detect NVM Node path
if [ -d "$HOME_DIR/.nvm" ]; then
    NVM_DIR="$HOME_DIR/.nvm"
    NODE_PATH=$(ls -d $NVM_DIR/versions/node/*/bin 2>/dev/null | sort -V | tail -n 1)
else
    echo "NVM not found. Please ensure Node is installed."
    exit 1
fi

if [ -z "$NODE_PATH" ]; then
    echo "No Node versions found in NVM."
    exit 1
fi

echo "Detected Node path: $NODE_PATH"

# Ask for port number
echo ""
read -p "[3/3] Enter a PORT number for frontend: " PORT

# Check if input contains only digits
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "Error: PORT must contain only numbers."
    exit 1
fi

# Check valid port range
if [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "Error: PORT must be between 1 and 65535."
    exit 1
fi
#####################################################
# Create start_app.sh
cat > "$PROJECT_PATH/start_app.sh" <<EOF
#!/bin/bash

# Load NVM environment
export NVM_DIR="$HOME_DIR/.nvm"
[ -s "\$NVM_DIR/nvm.sh" ] && \. "\$NVM_DIR/nvm.sh"

$VENV_SOURCE

# Start Flask backend
cd $PROJECT_PATH/backend || exit 1
nohup $PYTHON_CMD app.py > backend.log 2>&1 &

# Start React frontend
cd $PROJECT_PATH/frontend || exit 1
nohup serve -s build -l $PORT > frontend.log 2>&1 &
EOF

chmod +x "$PROJECT_PATH/start_app.sh"

echo "- Created $PROJECT_PATH/start_app.sh"

#####################################################
# Create systemd service

sudo bash -c "cat > $BACKEND_SERVICE_FILE" <<EOF
[Unit]
Description=Flask and React Surveillance App
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$PROJECT_PATH/backend

ExecStart=/usr/bin/python3 $PROJECT_PATH/backend/app.py

Restart=always
RestartSec=5

StandardOutput=append:$HOME_DIR/backend.log
StandardError=append:$HOME_DIR/backend_error.log

[Install]
WantedBy=multi-user.target
EOF

echo "- Created surveillance_app.service"

#####################################################
# Create frontend systemd service

sudo bash -c "cat > $FRONTEND_SERVICE_FILE" <<EOF
[Unit]
Description=Flask and React Surveillance App
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$PROJECT_PATH/frontend

Environment=NVM_DIR=$HOME_DIR/.nvm
Environment=PATH=$NODE_PATH:/usr/local/bin:/usr/bin:/bin

ExecStart=$NODE_PATH/serve -s build -l $PORT

Restart=always
RestartSec=5

StandardOutput=append:$HOME_DIR/frontend.log
StandardError=append:$HOME_DIR/frontend_error.log

[Install]
WantedBy=multi-user.target
EOF

echo "- Created surveillance_frontend.service"

#####################################################
# Reload and enable service
sudo systemctl daemon-reload
sudo systemctl enable surveillance_backend.service
sudo systemctl enable surveillance_frontend.service
echo "-------------------------------------------"
echo "Installation complete!"
echo "Start the service with:"
echo "  sudo systemctl start surveillance_backend.service"
echo "  sudo systemctl start surveillance_frontend.service"
echo "Check status with:"
echo "  sudo systemctl status surveillance_backend.service"
echo "  sudo systemctl status surveillance_frontend.service"
