#!/bin/bash
set -euo pipefail
pip install --upgrade pip
pip install -r requirements.txt
python -m bot
