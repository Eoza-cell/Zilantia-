#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Run the database setup script only if the DB doesn't exist
if [ ! -f aetheris.db ]; then
    echo "Database aetheris.db not found. Running database setup..."
    python3 database_setup.py
fi

# Start the bot
echo "Starting Aetheris bot..."
python3 aetheris_bot.py
