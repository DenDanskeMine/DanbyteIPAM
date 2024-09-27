import sys
import os

# Add the parent directory of 'src' to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run snmp_switch
from src.snmp_switch import snmp_switch

# Call the function or run as needed
async def main():
    await snmp_switch()

# Run the script asynchronously
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
