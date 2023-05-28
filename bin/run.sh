#!/bin/bash

# Run from the root directory
pip install -r requirements.txt &&\
  python src/manage.py migrate &&\
  nohup python src/run.py > scoreboard.log &
