"""SSH Manager for connecting to switches and executing commands"""
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
import logging

logger = logging.getLogger(__name__)


class SSHManager:
    """Manages SSH/Telnet connections to network switches with automatic fallback"""

    def __init__(self, host, username, password, device_type='huawei'):
        self.host = host
        self.username = username
        self.password = password
        self.device_type = device_type
        self.connection = None
        self.connection_method = None  # 'SSH' or 'Telnet'

    def connect(self):
        """Establish connection to switch - SSH first, then Telnet fallback"""
        ssh_error = None

        # Prima prova SSH
        try:
            device = {
                'device_type': 'huawei',
                'host': self.host,
                'username': self.username,
                'password': self.password,
                'port': 22,
                'timeout': 60,
                'session_timeout': 60,
                'conn_timeout': 15,  # Ridotto per velocizzare fallback
            }

            logger.info(f"Trying SSH connection to {self.host}...")
            self.connection = ConnectHandler(**device)
            self.connection_method = 'SSH'
            logger.info(f"SSH connection successful to {self.host}")

            # Disable pagination
            try:
                self.connection.send_command("screen-length disable")
                logger.info("Disabled pagination on device")
            except Exception as e:
                logger.warning(f"Could not disable pagination: {e}")

            return True

        except NetmikoAuthenticationException as e:
            # Errore autenticazione - non provare Telnet con stesse credenziali
            logger.error(f"Authentication failed for {self.host}: {str(e)}")
            raise Exception(f"Authentication failed: Invalid username or password")

        except (NetmikoTimeoutException, Exception) as e:
            ssh_error = str(e)
            logger.warning(f"SSH failed for {self.host}: {ssh_error}. Trying Telnet...")

        # Fallback a Telnet
        try:
            device = {
                'device_type': 'huawei_telnet',
                'host': self.host,
                'username': self.username,
                'password': self.password,
                'port': 23,
                'timeout': 60,
                'session_timeout': 60,
                'conn_timeout': 30,
            }

            logger.info(f"Trying Telnet connection to {self.host}...")
            self.connection = ConnectHandler(**device)
            self.connection_method = 'Telnet'
            logger.info(f"Telnet connection successful to {self.host}")

            # Disable pagination
            try:
                self.connection.send_command("screen-length disable")
                logger.info("Disabled pagination on device")
            except Exception as e:
                logger.warning(f"Could not disable pagination: {e}")

            return True

        except NetmikoAuthenticationException as e:
            logger.error(f"Telnet authentication failed for {self.host}: {str(e)}")
            raise Exception(f"Authentication failed: Invalid username or password")

        except Exception as telnet_error:
            logger.error(f"Both SSH and Telnet failed for {self.host}")
            raise Exception(f"Connection failed - SSH: {ssh_error}, Telnet: {str(telnet_error)}")

    def execute_command(self, command, handle_pagination=False):
        """
        Execute a command on the switch

        Note: Pagination is now disabled at connection time with 'screen-length disable'
        so handle_pagination is kept for backward compatibility but not used by default

        Args:
            command: Command to execute
            handle_pagination: Legacy parameter, kept for compatibility
        """
        if not self.connection:
            raise Exception("Not connected to switch")

        try:
            logger.info(f"Executing command: {command}")

            # Standard command execution (pagination disabled at connection)
            output = self.connection.send_command(command, read_timeout=60)
            return output

        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            raise Exception(f"Command execution failed: {str(e)}")

    def get_interface_brief(self):
        """Get brief interface information"""
        return self.execute_command("display interface brief")

    def get_interface_config(self, interface_name):
        """Get configuration for a specific interface"""
        return self.execute_command(f"display current-configuration interface {interface_name}")

    def get_all_interfaces_config(self):
        """Get all interface configurations"""
        return self.execute_command("display current-configuration | include interface")

    def disconnect(self):
        """Close SSH connection"""
        if self.connection:
            self.connection.disconnect()
            logger.info(f"Disconnected from {self.host}")
            self.connection = None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
