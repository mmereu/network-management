"""Parser for Huawei/HP switch configurations - Universal Multi-Vendor Support"""
import re
import logging
from app.universal_interface_parser import UniversalInterfaceParser

logger = logging.getLogger(__name__)


class ConfigParser:
    """Parse switch configuration output"""

    @staticmethod
    def parse_interface_brief(output):
        """
        Parse 'display interface brief' output from any vendor (Huawei, HP, Cisco)
        Uses UniversalInterfaceParser to recognize all interface nomenclatures
        Returns list of interfaces with basic info
        """
        interfaces = []

        # Extract all interface names using universal parser
        interface_names = UniversalInterfaceParser.extract_interfaces_from_output(output)

        lines = output.split('\n')
        for line in lines:
            line_strip = line.strip()

            # Check if this line contains one of the recognized interfaces
            for intf_name in interface_names:
                if line_strip.startswith(intf_name):
                    # Match interface lines like: GigabitEthernet0/0/1  UP  UP  or Eth1/0/1  UP  UP
                    match = re.match(r'^([\w/]+)\s+(\w+)\s+(\w+)', line_strip)
                    if match:
                        interface = {
                            'name': match.group(1),
                            'physical_status': match.group(2),
                            'protocol_status': match.group(3)
                        }
                        interfaces.append(interface)
                    break

        logger.info(f"Parsed {len(interfaces)} interfaces from brief output using universal parser")
        return interfaces

    @staticmethod
    def parse_interface_config(output):
        """
        Parse 'display current-configuration interface' output
        Returns dict with interface configuration
        """
        config = {
            'name': None,
            'description': None,
            'port_link_type': None,
            'vlan': None,
            'trunk_vlans': [],
            'speed': None,
            'duplex': None,
            'shutdown': False,
            'raw_config': []
        }

        lines = output.split('\n')
        for line in lines:
            line = line.strip()

            # Interface name
            if line.startswith('interface '):
                config['name'] = line.split()[1]

            # Description
            elif line.startswith('description '):
                config['description'] = line.replace('description ', '')

            # Port link type
            elif 'port link-type' in line:
                if 'access' in line:
                    config['port_link_type'] = 'access'
                elif 'trunk' in line:
                    config['port_link_type'] = 'trunk'

            # Default VLAN (access mode)
            # Huawei: "port default vlan 10"
            # HP: "port access vlan 10"
            elif 'port default vlan' in line or 'port access vlan' in line:
                vlan_match = re.search(r'vlan\s+(\d+)', line)
                if vlan_match:
                    config['vlan'] = int(vlan_match.group(1))
                    # Both Huawei "port default vlan" and HP "port access vlan" imply access mode
                    # Set access mode if not already set (fixes bug: missing port link-type line)
                    if not config['port_link_type']:
                        config['port_link_type'] = 'access'

            # Trunk VLANs
            # Huawei: "port trunk allow-pass vlan 10 20 30"
            # HP: "port trunk permit vlan all" or "port trunk permit vlan 10 20"
            elif 'port trunk allow-pass vlan' in line or 'port trunk permit vlan' in line:
                # Set link type to trunk
                if not config['port_link_type']:
                    config['port_link_type'] = 'trunk'

                # Check for "all" keyword (HP syntax)
                if 'vlan all' in line.lower():
                    # "permit vlan all" means all VLANs from 2 to 4094
                    config['trunk_vlans'] = list(range(2, 4095))
                else:
                    # Extract specific VLAN numbers
                    vlan_match = re.findall(r'\d+', line)
                    config['trunk_vlans'] = [int(v) for v in vlan_match]

            # Speed
            elif line.startswith('speed '):
                config['speed'] = line.split()[1]

            # Duplex
            elif line.startswith('duplex '):
                config['duplex'] = line.split()[1]

            # Shutdown
            elif line == 'shutdown':
                config['shutdown'] = True

            # Store raw config lines
            if line and not line.startswith('#'):
                config['raw_config'].append(line)

        logger.info(f"Parsed configuration for interface {config['name']}")
        return config

    @staticmethod
    def extract_interface_number(interface_name):
        """
        Extract slot and port number from interface name using universal parser
        Supports all vendor formats (Huawei, HP, Cisco, etc.)

        Examples:
            GigabitEthernet0/0/1 -> (0, 0, 1)
            Eth1/0/5 -> (1, 0, 5)
            GE0/0/24 -> (0, 0, 24)
        """
        parsed = UniversalInterfaceParser.parse_interface_name(interface_name)

        if parsed:
            return parsed['stack'], parsed['slot'], parsed['port']

        return None, None, None
