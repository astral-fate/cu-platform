#!/bin/bash
set -e
echo "--- build.sh script started ---"
python3 populate_db.py
echo "--- build.sh script finished ---"
