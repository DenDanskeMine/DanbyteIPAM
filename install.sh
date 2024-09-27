#!/bin/bash

# Exit if any command fails
set -e

# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the current user's home directory
USER_HOME=$(eval echo "~$USER")

# Paths for your project
PROJECT_DIR="$USER_HOME/DanbyteIPAM"
PYTHON_SCRIPT="$PROJECT_DIR/src/snmp_switch.py"
RUN_SNMP_SCRIPT="$PROJECT_DIR/run_snmp_loop.sh"
LOG_FILE="$USER_HOME/snmp_log.log"

# Update system and install necessary packages
echo -e "${BLUE}Updating system and installing dependencies...${NC}"
sudo apt update
sudo apt install -y python3-pip python3-venv mariadb-server npm libsnmp-dev snmp-mibs-downloader

# Reconfigure MariaDB
echo -e "${BLUE}Reconfiguring MariaDB...${NC}"
sudo dpkg-reconfigure mariadb-server

# Setting up virtual environment and installing Python dependencies
echo -e "${BLUE}Setting up Python virtual environment...${NC}"
python3 -m venv "$PROJECT_DIR/venv"
source "$PROJECT_DIR/venv/bin/activate"

# Install Python dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip install -r "$PROJECT_DIR/requirements.txt"

# Install Tailwind CSS dependencies using npm
echo -e "${BLUE}Installing Tailwind CSS and other dependencies...${NC}"
npm install --prefix "$PROJECT_DIR"

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
sudo mysql -u root -pCHANGEME <<MYSQL_SCRIPT
DROP USER IF EXISTS 'danbyte_admin'@'%';
CREATE DATABASE IF NOT EXISTS DANBYTE;
CREATE USER 'danbyte_admin'@'%' IDENTIFIED BY 'admin';
GRANT ALL PRIVILEGES ON DANBYTE.* TO 'danbyte_admin'@'%';
FLUSH PRIVILEGES;
MYSQL_SCRIPT

# Import database schema
echo -e "${BLUE}Importing database schema...${NC}"
mysql -u danbyte_admin -padmin DANBYTE < "$PROJECT_DIR/database.sql"

# Deactivate virtual environment
deactivate

# Tailwind CSS build (Optional, if required in your project)
echo -e "${BLUE}Entering venv${NC}"
source "$PROJECT_DIR/venv/bin/activate"

# Create the dynamic run_snmp.sh script to run SNMP collection every 20 seconds
cat <<EOF > "$RUN_SNMP_SCRIPT"
#!/bin/bash
while true; do
    python3 "$PYTHON_SCRIPT"
    sleep 20
done
EOF 

# Make the run_snmp.sh script executable
chmod +x "$RUN_SNMP_SCRIPT"

# Add cron job to run the SNMP collection script at boot
echo -e "${BLUE}Adding cron job to run SNMP script at boot...${NC}"
(crontab -l ; echo "@reboot $RUN_SNMP_SCRIPT > $LOG_FILE 2>&1") | crontab -

# Final messages
echo -e "${GREEN}Installation completed!${NC}"
echo -e "${YELLOW}Run the following command to start the application:${NC}"
echo " "
echo -e "${BLUE}uvicorn src.app:asgi_app --host 0.0.0.0 --port 8000 --reload${NC}"
echo " "
echo -e "${RED}Don't forget to change the database password in the settings.py file!${NC}"
echo " "
echo " "
echo -e "${YELLOW}Default ADMIN login credentials:${NC}"
echo -e "${GREEN}Username: admin${NC}"
echo -e "${GREEN}Password: admin${NC}"
echo " "
echo -e "${YELLOW}Default login credentials:${NC}"
echo -e "${GREEN}Username: user${NC}"
echo -e "${GREEN}Password: user${NC}"
echo " "
echo -e "${RED}Please change the default passwords after logging in!${NC}"

exit 0
