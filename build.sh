#!/bin/bash
set -e
echo "--- build.sh script started ---"
python populate_db.py
echo "--- build.sh script finished ---"
