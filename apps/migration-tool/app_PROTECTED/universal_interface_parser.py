"""Universal interface parser supporting multiple vendor formats"""
import re
import logging

logger = logging.getLogger(__name__)


class UniversalInterfaceParser:
    """Parse interface names from multiple vendors"""

    # Supported interface patterns with their normalization
    INTERFACE_PATTERNS = [
        # Huawei patterns
        {
            'name': 'Huawei GigabitEthernet',
            'pattern': r'(GigabitEthernet)(\d+)/(\d+)/(\d+)',
            'format': 'full',  # stack/slot/port
        },
        {
            'name': 'Huawei GE Short',
            'pattern': r'(GE)(\d+)/(\d+)/(\d+)',
            'format': 'full',
        },
        {
            'name': 'Huawei Ethernet',
            'pattern': r'(Ethernet)(\d+)/(\d+)/(\d+)',
            'format': 'full',
        },
        # HP patterns
        {
            'name': 'HP Eth',
            'pattern': r'(Eth)(\d+)/(\d+)/(\d+)',
            'format': 'full',
        },
        {
            'name': 'HP GigabitEthernet',
            'pattern': r'(GigabitEthernet)(\d+)/(\d+)/(\d+)',
            'format': 'full',
        },
        # Cisco patterns (2-segment)
        {
            'name': 'Cisco GigabitEthernet',
            'pattern': r'(GigabitEthernet)(\d+)/(\d+)',
            'format': 'slot_port',  # slot/port
        },
        {
            'name': 'Cisco FastEthernet',
            'pattern': r'(FastEthernet)(\d+)/(\d+)',
            'format': 'slot_port',
        },
        # Generic fallback
        {
            'name': 'Generic Interface',
            'pattern': r'((?:Gigabit|Fast)?Ethernet|Eth|GE)[\d/]+',
            'format': 'generic',
        }
    ]

    @staticmethod
    def parse_interface_name(interface_name):
        """
        Parse any interface name and extract components

        Returns:
            dict with: {
                'original': original name,
                'vendor_type': detected vendor/type,
                'prefix': interface prefix (GigabitEthernet, Eth, etc.),
                'stack': stack number,
                'slot': slot number,
                'port': port number,
                'format': format type
            }
        """
        for pattern_info in UniversalInterfaceParser.INTERFACE_PATTERNS:
            match = re.match(pattern_info['pattern'], interface_name)
            if match:
                groups = match.groups()

                result = {
                    'original': interface_name,
                    'vendor_type': pattern_info['name'],
                    'prefix': groups[0],
                    'format': pattern_info['format']
                }

                if pattern_info['format'] == 'full':
                    # stack/slot/port format
                    result['stack'] = int(groups[1])
                    result['slot'] = int(groups[2])
                    result['port'] = int(groups[3])
                elif pattern_info['format'] == 'slot_port':
                    # slot/port format (no stack)
                    result['stack'] = 0
                    result['slot'] = int(groups[1])
                    result['port'] = int(groups[2])
                else:
                    # Generic - extract all numbers
                    numbers = re.findall(r'\d+', interface_name)
                    result['stack'] = int(numbers[0]) if len(numbers) > 0 else 0
                    result['slot'] = int(numbers[1]) if len(numbers) > 1 else 0
                    result['port'] = int(numbers[2]) if len(numbers) > 2 else int(numbers[-1]) if numbers else 0

                logger.debug(f"Parsed {interface_name}: {result}")
                return result

        logger.warning(f"Could not parse interface: {interface_name}")
        return None

    @staticmethod
    def translate_to_new_format(parsed_interface, unit_number):
        """
        Translate parsed interface to new format: GE {unit}/{slot}/{port}

        Args:
            parsed_interface: Result from parse_interface_name()
            unit_number: New stack unit number (1, 2, 3, etc.)

        Returns:
            New interface name in format "GE {unit}/{slot}/{port}"
        """
        if not parsed_interface:
            return None

        slot = parsed_interface['slot']
        port = parsed_interface['port']

        new_name = f"GE {unit_number}/{slot}/{port}"

        logger.info(f"Translated {parsed_interface['original']} -> {new_name} (unit={unit_number})")
        return new_name

    @staticmethod
    def extract_interfaces_from_output(output):
        """
        Extract all interface names from command output

        Returns:
            List of unique interface names found
        """
        all_interfaces = set()

        for pattern_info in UniversalInterfaceParser.INTERFACE_PATTERNS[:-1]:  # Skip generic fallback
            matches = re.findall(pattern_info['pattern'], output)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        # Reconstruct full interface name from groups
                        if pattern_info['format'] == 'full':
                            interface = f"{match[0]}{match[1]}/{match[2]}/{match[3]}"
                        elif pattern_info['format'] == 'slot_port':
                            interface = f"{match[0]}{match[1]}/{match[2]}"
                        else:
                            interface = ''.join(match)
                    else:
                        interface = match

                    all_interfaces.add(interface)

        return sorted(list(all_interfaces))


# Backward compatibility function
def parse_interface_name(interface_name):
    """Backward compatible wrapper"""
    return UniversalInterfaceParser.parse_interface_name(interface_name)


def translate_interface_name(interface_name, unit_number):
    """Backward compatible wrapper"""
    parsed = UniversalInterfaceParser.parse_interface_name(interface_name)
    return UniversalInterfaceParser.translate_to_new_format(parsed, unit_number)
