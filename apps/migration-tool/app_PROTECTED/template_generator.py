"""Generate new switch configurations from templates"""
from jinja2 import Environment, FileSystemLoader
import os
import logging

logger = logging.getLogger(__name__)


class TemplateGenerator:
    """Generate Huawei switch configurations using Jinja2 templates"""

    def __init__(self, template_dir='templates/config_templates'):
        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def generate_complete_config(self, interfaces, switch_name, switch_ip, switch_gateway, admin_password,
                                   lacp_enabled=False, stack_units=None, switches_info=None):
        """
        Generate complete switch configuration with full template

        Args:
            interfaces: List of interface configuration dicts
            switch_name: New switch sysname
            switch_ip: Management IP address
            switch_gateway: Default gateway IP
            admin_password: Admin user password
            lacp_enabled: Enable LACP Eth-Trunk1 configuration
            stack_units: List of stack unit numbers for 10GE uplinks
            switches_info: List of switch info dicts with port_count per unit

        Returns:
            String with complete configuration
        """
        try:
            template = self.env.get_template('huawei_complete.j2')

            config = template.render(
                switch_name=switch_name,
                switch_ip=switch_ip,
                switch_gateway=switch_gateway,
                admin_password=admin_password,
                interfaces=interfaces,
                lacp_enabled=lacp_enabled,
                stack_units=stack_units or [],
                switches_info=switches_info or []
            )

            logger.info(f"Generated complete configuration for {switch_name} with {len(interfaces)} interfaces, LACP={lacp_enabled}")
            return config

        except Exception as e:
            logger.error(f"Complete template generation failed: {str(e)}")
            raise

    def generate_config(self, interfaces, admin_password='ChangeMe123', hostname='NewSwitch'):
        """
        Generate complete switch configuration

        Args:
            interfaces: List of interface configuration dicts
            admin_password: New admin password
            hostname: Switch hostname

        Returns:
            String with complete configuration
        """
        try:
            template = self.env.get_template('huawei_base.j2')

            config = template.render(
                hostname=hostname,
                admin_password=admin_password,
                interfaces=interfaces
            )

            logger.info(f"Generated configuration for {len(interfaces)} interfaces")
            return config

        except Exception as e:
            logger.error(f"Template generation failed: {str(e)}")
            raise

    def generate_simple_config(self, interfaces):
        """
        Generate simplified configuration (interface configs only)

        Args:
            interfaces: List of interface configuration dicts

        Returns:
            String with interface configurations
        """
        config_lines = ["system-view", ""]

        for iface in interfaces:
            config_lines.append(f"interface {iface['name']}")

            if iface.get('description'):
                config_lines.append(f" description {iface['description']}")

            if iface.get('port_link_type'):
                config_lines.append(f" port link-type {iface['port_link_type']}")

            if iface.get('port_link_type') == 'access' and iface.get('vlan'):
                config_lines.append(f" port default vlan {iface['vlan']}")

            if iface.get('port_link_type') == 'trunk' and iface.get('trunk_vlans'):
                vlans = ' '.join(map(str, iface['trunk_vlans']))
                config_lines.append(f" port trunk allow-pass vlan {vlans}")

            if iface.get('speed'):
                config_lines.append(f" speed {iface['speed']}")

            if iface.get('duplex'):
                config_lines.append(f" duplex {iface['duplex']}")

            config_lines.append(" quit")
            config_lines.append("")

        config_lines.extend(["quit", "save", "y"])

        return '\n'.join(config_lines)

    @staticmethod
    def format_config_for_download(config, filename='new_switch_config.cfg'):
        """
        Format configuration for file download

        Returns:
            tuple: (config_string, filename, mimetype)
        """
        return config, filename, 'text/plain'
