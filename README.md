# DanbyteIPAM

DanbyteIPAM is an advanced IP Address Management (IPAM) system designed to simplify network management tasks such as managing switches, subnets, and IP addresses. The platform offers a modern UI with real-time updates, efficient SNMP data collection, and user-friendly management of network resources.

![DanbyteIPAM Logo](https://github.com/user-attachments/assets/7cd80ec6-17f1-4bc1-9936-d4886dc7dc95)

## Features

- **IP Address Management**: Easily manage your network's IP addresses with real-time status updates.
- **Switch & Subnet Overview**: Monitor favorite switches and subnets with visual cues and sorting capabilities.
- **SNMP Data Collection**: Collect and refresh SNMP data for switches to ensure you always have the latest status.
- **Favorite IPs**: Keep track of important IPs by marking them as favorites.
- **Toggle-based Management**: Use simple toggle switches to manage the resolvability, gateway status, and visibility of IPs.

![DanbyteIPAM UI](https://github.com/user-attachments/assets/19cb3592-aa75-4b2b-8364-b203eecd1c6a)

## Getting Started

### Prerequisites

- **Python 3.x**
- **Flask**
- **MariaDB**
- **Tailwind CSS**
- **Jinja2**

### Installation
```bash
git clone -b PRE-DEMO https://github.com/DenDanskeMine/DanbyteIPAM.git 
cd DanbyteIPAM
chmod +x install.sh
./install.sh
```
 
run with: 
```bash
uvicorn src.app:asgi_app --host 0.0.0.0 --port 8000 --reload
```

access the web interface at http://localhost:8000

Usage
Switch Management: Navigate to the Switches section to view and update your favorite switches.
Subnet Management: View subnets and their associated IP addresses.
IP Management: Add, edit, and delete IP addresses within subnets. Toggle their gateway, resolvable, and status directly from the UI.
Contributing
We welcome contributions! Please feel free to submit issues, pull requests, and feature suggestions to improve the DanbyteIPAM system.

License
This project is licensed under the MIT License. See the LICENSE file for details.

