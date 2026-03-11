# Surveillance Camera App

This project is for making an autonomous surveilance system using any usb-camera, pi-camera on raspberry pi, jetson nano or any single board computer that can run python flask app, npm.

## Features

- Creating a user account with predefined registration code
- Live view from the camera
- User can Arm/Disarm motion detection
- Automatic video recording for any detected motion
- Auto removing recorded video after user defined period


## Installation

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

1. Install `node v17` or later
    - Raspberry pi with `uname -r` over `6.1.21-v8+` can install node v22 or later
    - For jetson nano
        - node v18 or later would not work due to libc version issue
        - Install node using `nvm` is recommended 
        ```
        nvm install v17
        nvm alias default v17
        nvm use v17
        ```
        
2. Install packages for backend
    ```
    cd backend/
    pip3 install --upgrade pip setuptools wheel
    pip3 install -r requirements.txt 
    ```
    For jetson nano, some packages may not work. So install specific versions
    ```
    pip3 uninstall flask-socketio python-socketio python-engineio -y
    pip3 install flask-socketio==5.3.6
    pip3 install python-socketio==5.8.0
    pip3 install python-engineio==4.4.1
    ```
    
3. Create `.env` files for `backend`
    ```
    MAIL_USERNAME=                # Your email
    MAIL_PASSWORD=                # Your email password
    SECRET_KEY=                   # Your Registraion Code
    DATABASE_URL=sqlite:///surveillance.db
    MAIL_PASSKEY=                 # Your email pass key
    EXTERNAL_IP=                  # External IP address assigned to your router
    ```

4. Install packages for frontend
    ```
    cd frontend/
    npm install
    npm audit fix   # If required
    npm install -g serve # install serve globally 
    ```

5. Create `.env` file for `frontend`
    ```
    REACT_APP_API_BASE_URL=http://IP_ADDRESS:5000
    ```


## Run app in terminal

1. Open 2 terminals or ssh connection.

2. In the first terminal, start frontend 
    ```
    cd frontend/
    npm start
    ```

3. In the second terminal, start backend app
    ```
    cd backend/
    python3 app.y
    ```

## Start app as systemd service

1. Build frontend for serve (Make sure .env file exist)
    ```
    cd frontend/
    npm run build
    ```
    
2. try run `serve` to check if everything works
    ```
    serve -s build -l 3000
    ```
    
3. Run `install_app.sh` to install `surveillance_frontend.service` and `surveillance_backend.service` 

4. Start fronend and backend separately
    ```
    sudo systemctl daemon-reload
    sudo systemctl start surveillance_frontend.service
    sudo systemctl start surveillance_backend.service
    ```

