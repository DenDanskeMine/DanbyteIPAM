#!/bin/bash

# Exit if any command fails
set -e

# Update system and install necessary packages
echo "Updating system and installing dependencies..."
sudo apt update
sudo apt install -y python3-pip python3-venv mariadb-server npm

# Setting up virtual environment and installing Python dependencies
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install Tailwind CSS dependencies using npm
echo "Installing Tailwind CSS and other dependencies..."
npm install

# Start MariaDB service
echo "Starting MariaDB service..."
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Secure MariaDB installation
echo "Securing MariaDB installation..."
sudo mysql_secure_installation

# Create MariaDB user and database
echo "Creating MariaDB user and database..."
sudo mysql -u root -p <<MYSQL_SCRIPT
CREATE DATABASE DANBYTE;
CREATE USER 'danbyte_admin'@'%' IDENTIFIED BY 'admin';
GRANT ALL PRIVILEGES ON DANBYTE.* TO 'danbyte_admin'@'%';
FLUSH PRIVILEGES;
MYSQL_SCRIPT

# Import database schema
echo "Importing database schema..."
sudo mysql -u danbyte_admin -padmin DANBYTE < database.sql

# Deactivate virtual environment
deactivate

# Tailwind CSS build (Optional, if required in your project)
echo "Building Tailwind CSS..."
npm run build

echo "Installation completed!"
