#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Run the database setup script
echo "Running database setup..."
python3 database_setup.py

# Start the bot
echo "Starting the bot..."
python3 arcanes_bot.py
