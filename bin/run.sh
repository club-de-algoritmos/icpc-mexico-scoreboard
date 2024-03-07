#!/bin/bash

set -e

scoreboard_pid=$(ps -aux | grep run_scoreboard | grep -v grep | awk '{ print $2 }')
if [ -z "$scoreboard_pid" ]; then
  echo "scoreboard was not running";
else
  echo "scoreboard is running and will now be killed...";
  kill "$scoreboard_pid"
fi

sleep 2

# Run from the root directory
pip install -r requirements.txt
python src/manage.py migrate
nohup python src/run_scoreboard.py > scoreboard.log 2>&1 &

echo "scoreboard is now running!"
echo
