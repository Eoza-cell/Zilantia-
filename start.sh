#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Check if the database file exists and run setup only if it doesn't
if [ ! -f "zilantia.db" ]; then
    echo "Database file 'zilantia.db' not found. Running setup..."
    python3 database_setup.py
else
    echo "Database file 'zilantia.db' found. Skipping setup."
fi

# Start the bot
echo "Starting the bot..."
python3 zilantia_bot.py
