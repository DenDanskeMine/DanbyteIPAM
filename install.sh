#!/bin/bash

# Exit if any command fails
set -e

# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Update system and install necessary packages
echo -e "${BLUE}Updating system and installing dependencies...${NC}"
sudo apt update
sudo apt install -y python3-pip python3-venv mariadb-server npm libsnmp-dev snmp-mibs-downloader

# Setting up virtual environment and installing Python dependencies
echo -e "${BLUE}Setting up Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Install Tailwind CSS dependencies using npm
echo -e "${BLUE}Installing Tailwind CSS and other dependencies...${NC}"
npm install

# Start MariaDB service
echo -e "${BLUE}Starting MariaDB service...${NC}"
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Secure MariaDB installation
echo -e "${BLUE}Securing MariaDB installation...${NC}"
sudo mysql_secure_installation <<EOF

y
CHANGEME
CHANGEME
y
y
y
y
EOF

# Create MariaDB user and database
echo -e "${BLUE}Creating MariaDB user and database...${NC}"
mysql -u root -pCHANGEME <<MYSQL_SCRIPT
DROP USER IF EXISTS 'danbyte_admin'@'%';
CREATE DATABASE IF NOT EXISTS DANBYTE;
CREATE USER 'danbyte_admin'@'%' IDENTIFIED BY 'admin';
GRANT ALL PRIVILEGES ON DANBYTE.* TO 'danbyte_admin'@'%';
FLUSH PRIVILEGES;
MYSQL_SCRIPT

# Import database schema
echo -e "${BLUE}Importing database schema...${NC}"
mysql -u danbyte_admin -padmin DANBYTE < database.sql

# Deactivate virtual environment
deactivate

# Tailwind CSS build (Optional, if required in your project)
echo -e "${BLUE}Entering venv${NC}"
source venv/bin/activate

# Final messages
echo -e "${GREEN}Installation completed!${NC}"
source venv/bin/activate
echo -e "${YELLOW}Run the following command to start the application:${NC}"
echo ""
echo -e "${BLUE}uvicorn src.app:asgi_app --host 0.0.0.0 --port 8000 --reload${NC}"
echo ""
echo -e "${RED}Don't forget to change the database password in the settings.py file!${NC}"
echo ""
echo ""
echo -e "${YELLOW}Default login credentials:${NC}"
echo -e "${GREEN}Username: admin${NC}"
echo -e "${GREEN}Password: admin${NC}"
echo ""
echo -e "${GREEN}Username: user${NC}"
echo -e "${GREEN}Password: user${NC}"
echo ""
echo -e "${RED}Please change the default password after logging in!${NC}"

uvicorn src.app:asgi_app --host 0.0.0.0 --port 8000 --reload