import re
import logging

def group_interfaces_by_stack(interfaces):
    stack_groups = {}
    grouped_interfaces = {}

    for interface in interfaces:
        name, status, shutdown = interface['name'], interface['status'], interface['shutdown']
        
        # Skip management, VLAN, and Null interfaces
        if re.match(r'(management|vlan|Null|DEFAULT_VLAN|Switch loopback interface|Out Of Band Management|v|lb)', name, re.IGNORECASE):
            continue
        
        # Updated regex to handle both prefixed and unprefixed interfaces
        match = re.match(r'([a-zA-Z]*\d*[a-zA-Z]*\d*)(?:Ethernet|GigE|channel)?\s*(\d+/\d+/\d+|\d+/\d+|\d+)', name, re.IGNORECASE)
        
        # Handle matches
        if match:
            interface_type = match.group(1).strip() if match.group(1) else 'Interface'  # Use a default 'Interface' if no prefix is found
            numbers = match.group(2).split('/')
            
            # Case 1: Interface has three parts like x/x/x (stack/group/interface)
            if len(numbers) == 3:
                stack, group, iface = numbers
                key = f"{interface_type} {stack}/{group}"
            
            # Case 2: Interface has two parts like x/x (stack/interface)
            elif len(numbers) == 2:
                stack, iface = numbers
                key = f"{interface_type} {stack}"
            
            # Case 3: Interface has only one part like x
            elif len(numbers) == 1:
                iface = numbers[0]
                stack = 'default'  # Assign a default stack value
                key = f"{interface_type} {iface}"
            else:
                logging.debug(f"Interface name '{name}' did not match expected patterns.")
                continue
            
            # Initialize the stack group if not already present
            if stack not in stack_groups:
                stack_groups[stack] = {'odd': [], 'even': []}
            
            # Initialize the key in the grouped interfaces if not present
            if key not in grouped_interfaces:
                grouped_interfaces[key] = {'odd': [], 'even': []}
            
            # Add the interface to both the stack and grouped interfaces
            if int(iface) % 2 == 0:
                stack_groups[stack]['even'].append({'name': name, 'status': status, 'shutdown': shutdown})
                grouped_interfaces[key]['even'].append({'name': name, 'status': status, 'shutdown': shutdown})
            else:
                stack_groups[stack]['odd'].append({'name': name, 'status': status, 'shutdown': shutdown})
                grouped_interfaces[key]['odd'].append({'name': name, 'status': status, 'shutdown': shutdown})
        else:
            logging.debug(f"Interface name '{name}' did not match expected patterns.")
            # Add unmatched interfaces to the default stack
            stack = 'Spacial Interfaces'
            key = f"Interface {name}"
            
            # Initialize the default stack group if not already present
            if stack not in stack_groups:
                stack_groups[stack] = {'odd': [], 'even': []}
            
            # Initialize the key in the grouped interfaces if not present
            if key not in grouped_interfaces:
                grouped_interfaces[key] = {'odd': [], 'even': []}
            
            # Add the interface to both the default stack and grouped interfaces
            stack_groups[stack]['odd'].append({'name': name, 'status': status, 'shutdown': shutdown})
            grouped_interfaces[key]['odd'].append({'name': name, 'status': status, 'shutdown': shutdown})
    
    logging.debug(f"Grouped interfaces: {grouped_interfaces}")
    logging.debug(f"Grouped interfaces by stack: {stack_groups}")
    
    return stack_groups, grouped_interfaces