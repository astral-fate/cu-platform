#!/bin/bash
set -e
echo "--- build.sh script started ---"
pip install -r requirements.txt
python populate_db.py
echo "--- build.sh script finished ---"
