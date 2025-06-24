#!/bin/bash

# This script will run during the build process on Vercel.

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- build.sh script started ---"

# The Vercel build environment automatically installs dependencies from requirements.txt,
# but we run it again here to be absolutely sure.
echo "Installing dependencies..."
pip install -r requirements.txt

# Now, run the database population script.
# This script needs the DATABASE_URL environment variable to be set in your Vercel project.
echo "Running database population script (populate_db.py)..."
python populate_db.py

echo "--- build.sh script finished ---"
