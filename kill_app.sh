#!/bin/bash

# Kills processes whose command contains "app.py"
ps aux | grep "app.py" | grep -v grep | awk '{print $2}' | xargs -r kill -9

# Kills processes whose command contains "serve -s"
ps aux | grep "serve -s" | grep -v grep | awk '{print $2}' | xargs -r kill -9

echo "Processes containing 'app.py' or 'serve -s' have been killed."
