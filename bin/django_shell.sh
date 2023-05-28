#!/bin/bash

# Run from the root directory
PYTHONSTARTUP=bin/django_shell_imports.py python src/manage.py shell -i ipython
