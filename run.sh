#!/bin/bash
echo "Checking for processes on port 8000"
if lsof -i :8000; then
    echo "Killing processes on port 8000"
    fuser -k 8000/tcp
else
    echo "No processes found on port 8000"
fi
echo "Killing any Uvicorn and Tailwind processes"
pkill -f uvicorn
pkill -f tailwindcss
echo "Changing to ~/FLASK directory"
cd ~/FLASK
echo "Activating virtual environment"
source venv/bin/activate
echo "Running npx TailwindCSS"
npx tailwindcss -i ./src/static/css/input.css -o ./src/static/css/output.css
echo "Starting Uvicorn server"
uvicorn src.app:asgi_app --host 0.0.0.0 --port 8000 --reload
