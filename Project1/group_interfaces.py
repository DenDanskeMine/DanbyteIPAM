import re
import logging

def group_interfaces_by_stack(interfaces):
    grouped_interfaces = {}
    stack_groups = {}

    logging.debug(f"Total interfaces before grouping: {len(interfaces)}")

    for interface in interfaces:
        name = interface['name']
        status = interface['status']
        shutdown = interface['shutdown']
        vlan = interface['vlan']
        mac = interface['mac']

        logging.debug(f"Processing interface: {name}, status: {status}, shutdown: {shutdown}, vlan: {vlan}, mac: {mac}")

        # Skip certain interfaces based on name patterns
        if re.match(r'(management|Null|DEFAULT_VLAN|Switch loopback interface|Out Of Band Management|v|lb)', name, re.IGNORECASE):
            logging.debug(f"Skipping interface: {name}")
            continue
        
        # Updated regex to handle both prefixed and unprefixed interfaces
        match = re.match(r'([a-zA-Z]*\d*[a-zA-Z]*\d*)(?:Ethernet)?(\d+/\d+/\d+|\d+/\d+|\d+|v\d+|lb\d+)', name)
        
        if match:
            interface_type = match.group(1).strip() if match.group(1) else 'Interface'  # Use a default 'Interface' if no prefix is found
            numbers = match.group(2).split('/')
            
            logging.debug(f"Matched interface: {name}, interface_type: {interface_type}, numbers: {numbers}")

            # Case 1: Interface has three parts like x/x/x (stack/group/interface)
            if len(numbers) == 3:
                stack, group, iface = numbers
                key = f"{interface_type} {stack}/{group}"
                logging.debug(f"Interface {name} has three parts: stack={stack}, group={group}, iface={iface}, key={key}")
            
            # Case 2: Interface has two parts like x/x (stack/interface)
            elif len(numbers) == 2:
                stack, iface = numbers
                key = f"{interface_type} {stack}"
                logging.debug(f"Interface {name} has two parts: stack={stack}, iface={iface}, key={key}")
            
            # Case 3: Interface has one part like x (interface)
            elif len(numbers) == 1:
                iface = numbers[0]
                key = interface_type
                logging.debug(f"Interface {name} has one part: iface={iface}, key={key}")
            else:
                logging.error(f"Unexpected number of parts in interface name: {name}")
                continue

            if key not in grouped_interfaces:
                grouped_interfaces[key] = {'odd': [], 'even': []}
            
            if int(iface) % 2 == 0:
                grouped_interfaces[key]['even'].append(interface)
                logging.debug(f"Added interface {name} to even group under key {key}")
            else:
                grouped_interfaces[key]['odd'].append(interface)
                logging.debug(f"Added interface {name} to odd group under key {key}")
        else:
            logging.debug(f"No match for interface: {name}")

    # Group interfaces by stack
    for key, groups in grouped_interfaces.items():
        stack = key.split()[1].split('/')[0]
        if stack not in stack_groups:
            stack_groups[stack] = {}
        stack_groups[stack][key] = groups

    logging.debug(f"Grouped interfaces by stack: {stack_groups}")
    logging.debug(f"Grouped interfaces: {grouped_interfaces}")
    return grouped_interfaces, stack_groups