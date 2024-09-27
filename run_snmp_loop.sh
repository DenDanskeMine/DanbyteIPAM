#!/bin/bash

# Path to your Python virtual environment and the script
cd /home/crosk/FLASK

# Run the SNMP script every 20 seconds
while true; do
    # Activate virtual environment and run the Python script
    source venv/bin/activate
    python run_snmp.py
    deactivate

    # Wait for 20 seconds before running the script again
#    sleep 20
done

