"""Flask routes for web interface - Updated for multi-vendor multi-switch support"""
from flask import Blueprint, render_template, request, jsonify, send_file
from app.ssh_manager import SSHManager
from app.config_parser import ConfigParser
from app.interface_translator import InterfaceTranslator
from app.template_generator import TemplateGenerator
from app.universal_interface_parser import UniversalInterfaceParser
import logging
import io
import os

logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Main web interface"""
    return render_template('index.html')


@bp.route('/extract_config', methods=['POST'])
def extract_config():
    """Extract configuration from old switch via SSH"""
    try:
        data = request.get_json()

        # Validate input
        required_fields = ['ip', 'username', 'password', 'unit_number', 'switch_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400

        ip = data['ip']
        username = data['username']
        password = data['password']
        unit_number = int(data['unit_number'])
        switch_type = data['switch_type']

        logger.info(f"Extracting config from {ip}, unit={unit_number}, type={switch_type}")

        # Connect to switch
        with SSHManager(ip, username, password) as ssh:
            # Get interface brief
            brief_output = ssh.get_interface_brief()
            interfaces_list = ConfigParser.parse_interface_brief(brief_output)

            # Get detailed config for each interface
            interfaces_config = []

            # Determine max port based on switch type (24 or 48)
            max_port = int(switch_type)  # switch_type is "24" or "48"

            for iface in interfaces_list:
                # Use universal parser to check if it's a physical interface
                parsed = UniversalInterfaceParser.parse_interface_name(iface['name'])
                if parsed:  # If parseable, it's a physical interface
                    # Filter: Skip uplink ports (port > max_port)
                    # For 24-port: skip ports 25, 26, 27, 28
                    # For 48-port: skip ports 49, 50, 51, 52
                    if parsed['port'] > max_port:
                        logger.info(f"Skipping uplink port {iface['name']} (port {parsed['port']} > {max_port})")
                        continue

                    try:
                        config_output = ssh.get_interface_config(iface['name'])
                        config = ConfigParser.parse_interface_config(config_output)

                        # Translate interface name (accepts all port numbers, all vendors)
                        config = InterfaceTranslator.translate_full_config(
                            config, unit_number, switch_type
                        )

                        interfaces_config.append(config)
                    except Exception as e:
                        logger.warning(f"Failed to get config for {iface['name']}: {str(e)}")

        logger.info(f"Successfully extracted {len(interfaces_config)} interface configs via {ssh.connection_method}")

        return jsonify({
            'success': True,
            'interfaces': interfaces_config,
            'count': len(interfaces_config),
            'connection_method': ssh.connection_method
        })

    except Exception as e:
        logger.error(f"Config extraction failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/generate_config', methods=['POST'])
def generate_config():
    """Generate new switch configuration (simple version)"""
    try:
        data = request.get_json()

        # Validate input
        required_fields = ['interfaces', 'unit_number']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        interfaces = data['interfaces']
        unit_number = data['unit_number']

        logger.info(f"Generating config for {len(interfaces)} interfaces, unit={unit_number}")

        # Generate configuration
        generator = TemplateGenerator()
        config = generator.generate_config(interfaces, unit_number)

        filename = f"switch_unit_{unit_number}_config.txt"

        return jsonify({
            'success': True,
            'config': config,
            'filename': filename
        })

    except Exception as e:
        logger.error(f"Config generation failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/generate_config_complete', methods=['POST'])
def generate_config_complete():
    """Generate complete switch configuration with all VLANs and settings"""
    try:
        data = request.get_json()

        # Validate input
        required_fields = ['interfaces', 'switch_name', 'switch_ip', 'switch_gateway', 'admin_password']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        interfaces = data['interfaces']
        switch_name = data['switch_name']
        switch_ip = data['switch_ip']
        switch_gateway = data['switch_gateway']
        admin_password = data['admin_password']

        logger.info(f"Generating complete config for {len(interfaces)} interfaces")

        # Generate complete configuration
        generator = TemplateGenerator()
        config = generator.generate_complete_config(
            interfaces, switch_name, switch_ip, switch_gateway, admin_password
        )

        filename = f"{switch_name}_complete_config.txt"

        return jsonify({
            'success': True,
            'config': config,
            'filename': filename
        })

    except Exception as e:
        logger.error(f"Complete config generation failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/download_config', methods=['POST'])
def download_config():
    """Download generated configuration file"""
    try:
        data = request.get_json()

        if 'config' not in data or 'filename' not in data:
            return jsonify({'error': 'Missing config or filename'}), 400

        config_content = data['config']
        filename = data['filename']

        # Create in-memory file
        file_buffer = io.BytesIO()
        file_buffer.write(config_content.encode('utf-8'))
        file_buffer.seek(0)

        return send_file(
            file_buffer,
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Config download failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


@bp.route('/api/process-stack', methods=['POST'])
def process_stack():
    """Process stack configuration - extract from multiple switches"""
    try:
        data = request.get_json()
        
        required_fields = ['stack_name', 'switches']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        stack_name = data['stack_name']
        switches = data['switches']
        
        if not switches or len(switches) == 0:
            return jsonify({'error': 'No switches provided'}), 400
        
        logger.info(f"Processing stack {stack_name} with {len(switches)} switches")
        
        all_interfaces = []
        stack_switches = []
        unique_vlans = set()
        
        for sw in switches:
            try:
                ip = sw['host']
                password = sw['password']
                unit = sw['unit']
                username = data.get('username', 'admin')
                
                logger.info(f"Extracting from {ip} unit {unit}")
                
                with SSHManager(ip, username, password) as ssh:
                    brief_output = ssh.get_interface_brief()
                    interfaces_list = ConfigParser.parse_interface_brief(brief_output)
                    
                    switch_interfaces = []
                    for iface in interfaces_list:
                        parsed = UniversalInterfaceParser.parse_interface_name(iface['name'])
                        if parsed:
                            try:
                                config_output = ssh.get_interface_config(iface['name'])
                                config = ConfigParser.parse_interface_config(config_output)
                                config = InterfaceTranslator.translate_full_config(config, unit, '48')
                                
                                switch_interfaces.append(config)
                                all_interfaces.append(config)
                                
                                if 'vlan' in config and config['vlan']:
                                    if isinstance(config['vlan'], list):
                                        unique_vlans.update(config['vlan'])
                                    else:
                                        unique_vlans.add(config['vlan'])
                                        
                            except Exception as e:
                                logger.warning(f"Failed config for {iface['name']}: {e}")
                
                stack_switches.append({
                    'stack_unit': unit,
                    'switch_ip': ip,
                    'ip_address': ip,
                    'interface_count': len(switch_interfaces),
                    'vlans': list(unique_vlans),
                    'connection_method': ssh.connection_method,
                    'error': None
                })
                
            except Exception as e:
                logger.error(f"Failed to process switch {sw.get('host', 'unknown')}: {e}")
                stack_switches.append({
                    'stack_unit': sw.get('unit', 0),
                    'switch_ip': sw.get('host', 'unknown'),
                    'ip_address': sw.get('host', 'unknown'),
                    'interface_count': 0,
                    'vlans': [],
                    'connection_method': None,
                    'error': str(e)
                })
        
        stack_summary = {
            'stack_name': stack_name,
            'switch_count': len(switches),
            'total_interfaces': len(all_interfaces),
            'vlans': sorted(list(unique_vlans)),
            'switches': stack_switches
        }
        
        # Store in session or temp file for step 3
        os.makedirs('/tmp/huawei_stack', exist_ok=True)
        import json
        with open(f'/tmp/huawei_stack/{stack_name}.json', 'w') as f:
            json.dump({'interfaces': all_interfaces, 'summary': stack_summary}, f)
        
        logger.info(f"Stack processing complete: {len(all_interfaces)} interfaces from {len(switches)} switches")
        
        return jsonify({
            'success': True,
            'message': f'Elaborati {len(switches)} switch con {len(all_interfaces)} interfacce',
            'stack_summary': stack_summary
        })
        
    except Exception as e:
        logger.error(f"Stack processing failed: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/generate-stack-config', methods=['POST'])
def generate_stack_config():
    """Generate final stack configuration"""
    try:
        data = request.get_json()
        
        required_fields = ['stack_name', 'new_stack_ip', 'gateway', 'admin_password']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        stack_name = data['stack_name']
        new_stack_ip = data['new_stack_ip']
        gateway = data['gateway']
        admin_password = data['admin_password']
        
        # Load interfaces from temp file
        import json
        stack_file = f'/tmp/huawei_stack/{stack_name}.json'
        
        if not os.path.exists(stack_file):
            return jsonify({'error': 'Stack data not found. Please process stack first (Step 2)'}), 400
        
        with open(stack_file, 'r') as f:
            stack_data = json.load(f)
        
        interfaces = stack_data['interfaces']
        
        logger.info(f"Generating stack config for {stack_name}: {len(interfaces)} interfaces")
        
        generator = TemplateGenerator()
        config = generator.generate_complete_config(
            interfaces, stack_name, new_stack_ip, gateway, admin_password
        )
        
        filename = f"{stack_name}_config.txt"
        
        # Save to file
        config_path = f'/tmp/huawei_stack/{filename}'
        with open(config_path, 'w') as f:
            f.write(config)
        
        return jsonify({
            'success': True,
            'message': 'Configurazione stack generata con successo',
            'config_filename': filename,
            'config_size': len(config),
            'config_content': config
        })
        
    except Exception as e:
        logger.error(f"Stack config generation failed: {e}")
        return jsonify({'error': str(e)}), 500
