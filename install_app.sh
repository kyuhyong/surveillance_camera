#!/bin/bash

echo "===== Surveillance App Installer ====="

# Get current project path
PROJECT_PATH="$(pwd)"
USER_NAME="$(whoami)"
HOME_DIR="$HOME"

echo "Project path detected: $PROJECT_PATH"
echo "User detected: $USER_NAME"

# Ask user about virtual environment
read -p "Do you want to use a virtual environment? (y/n): " USE_VENV

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
nohup serve -s build -l 3000 > frontend.log 2>&1 &
EOF

chmod +x "$PROJECT_PATH/start_app.sh"

echo "Created start_app.sh"

# Create systemd service
SERVICE_FILE="/etc/systemd/system/surveillance_app.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Flask and React Surveillance App
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$PROJECT_PATH
ExecStartPre=/bin/bash -c 'echo "Starting Surveillance App at \$(date)" >> $HOME_DIR/startup.log'
ExecStart=/bin/bash $PROJECT_PATH/start_app.sh
Restart=always
RestartSec=5
StartLimitInterval=0
TimeoutStartSec=300
Environment=PATH=$NODE_PATH:$VENV_PATH_EXPORT:/usr/local/bin:/usr/bin:/bin
Environment=NVM_DIR=$HOME_DIR/.nvm

[Install]
WantedBy=multi-user.target
EOF

echo "Created surveillance_app.service"

# Reload and enable service
sudo systemctl daemon-reload
sudo systemctl enable surveillance_app.service

echo "Installation complete!"
echo "Start the service with:"
echo "  sudo systemctl start surveillance_app.service"
echo "Check status with:"
echo "  sudo systemctl status surveillance_app.service"
