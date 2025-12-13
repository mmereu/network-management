"""Translate interface names from old to new format - Universal Multi-Vendor Support"""
import re
import logging
from app.universal_interface_parser import UniversalInterfaceParser

logger = logging.getLogger(__name__)


class InterfaceTranslator:
    """Translates interface names from any vendor format to new switch format"""

    @staticmethod
    def translate_interface_name(old_name, unit_number):
        """
        Translate interface name from any vendor format to new format

        Examples:
            GigabitEthernet0/0/1 with unit=1 -> GE 1/0/1
            Eth1/0/5 with unit=2 -> GE 2/0/5
            GigabitEthernet1/0/24 with unit=1 -> GE 1/0/24

        Args:
            old_name: Original interface name (any vendor format)
            unit_number: Stack unit number (1, 2, 3, etc.)

        Returns:
            New interface name (e.g., GE 1/0/1)
        """
        parsed = UniversalInterfaceParser.parse_interface_name(old_name)

        if not parsed:
            logger.warning(f"Could not parse interface name: {old_name}")
            return old_name

        new_name = UniversalInterfaceParser.translate_to_new_format(parsed, unit_number)
        logger.info(f"Translated {old_name} -> {new_name} (unit={unit_number})")

        return new_name

    @staticmethod
    def validate_port_number(port, switch_type):
        """
        Validate port number against switch type (optional, not enforced)

        Args:
            port: Port number to validate
            switch_type: '24' or '48' port switch

        Returns:
            bool: True if valid, False otherwise
        """
        max_ports = int(switch_type)

        if port < 1 or port > max_ports:
            logger.warning(f"Port number {port} exceeds {switch_type}-port switch capacity (not enforced)")
            return False

        return True

    @staticmethod
    def translate_full_config(config, unit_number, switch_type):
        """
        Translate full interface configuration from any vendor

        Args:
            config: Dictionary with interface configuration
            unit_number: Stack unit number
            switch_type: '24' or '48' (for reference only, not used for validation)

        Returns:
            Updated config dict with translated interface name
        """
        old_name = config.get('name', '')

        # Translate interface name (accepts all port numbers and all vendors)
        new_name = InterfaceTranslator.translate_interface_name(old_name, unit_number)
        config['name'] = new_name
        config['original_name'] = old_name

        return config
