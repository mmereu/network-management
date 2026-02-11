"""Flask routes for Config Backup API"""
from flask import Blueprint, request, jsonify, render_template, send_from_directory
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import requests

# Support both module and standalone execution
try:
    from .ssh_manager import SSHManager
    from .backup_manager import (
        save_backup,
        read_backup_file,
        get_diff_between_backups,
        get_latest_diff,
        BACKUPS_DIR,
    )
    from .csv_parser import parse_pdv_csv, get_site_by_id, get_sites_dropdown
    from . import database
except ImportError:
    from ssh_manager import SSHManager
    from backup_manager import (
        save_backup,
        read_backup_file,
        get_diff_between_backups,
        get_latest_diff,
        BACKUPS_DIR,
    )
    from csv_parser import parse_pdv_csv, get_site_by_id, get_sites_dropdown, get_all_credentials_for_site
    import database

logger = logging.getLogger(__name__)

bp = Blueprint('config_backup', __name__)


@bp.route('/')
def index():
    """Serve main UI"""
    return render_template('index.html')


@bp.route('/api/sites', methods=['GET'])
def get_sites():
    """
    Get list of sites from Pdv.CSV for dropdown.

    Returns:
        JSON with sites list
    """
    try:
        sites = parse_pdv_csv()
        dropdown = get_sites_dropdown()

        return jsonify({
            'success': True,
            'sites': sites,
            'dropdown': dropdown,
            'count': len(sites),
        })
    except Exception as e:
        logger.error(f"Error loading sites: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@bp.route('/api/backup', methods=['POST'])
def create_backup():
    """
    Create backup for a single device.

    Request JSON:
        - sito: Site ID (optional if ip provided)
        - ip: Device IP (optional if sito provided)
        - username: SSH username (optional if sito provided)
        - password: SSH password (optional if sito provided)
        - use_core: Use core switch credentials (default: true)

    Returns:
        JSON with backup result and diff
    """
    data = request.get_json() or {}

    sito = data.get('sito')
    ip = data.get('ip')
    username = data.get('username')
    password = data.get('password')
    use_core = data.get('use_core', True)

    # If sito provided, load credentials from CSV
    if sito and not ip:
        site = get_site_by_id(sito)
        if not site:
            return jsonify({
                'success': False,
                'error': f'Site not found: {sito}',
            }), 404

        ip = site['switch_core_ip']
        if use_core:
            username = site['utente_core'] or site['utente']
            password = site['password_core'] or site['password']
        else:
            username = site['utente']
            password = site['password']
        nome_sito = site['nome']
    else:
        nome_sito = data.get('nome_sito', '')

    # Validate required fields
    if not ip:
        return jsonify({
            'success': False,
            'error': 'IP address is required',
        }), 400

    if not username or not password:
        return jsonify({
            'success': False,
            'error': 'Username and password are required',
        }), 400

    try:
        # Connect and get configuration
        with SSHManager(ip, username, password) as ssh:
            config = ssh.get_current_configuration()
            connection_method = ssh.connection_method

        # Save backup
        result = save_backup(
            sito=sito or ip,
            nome_sito=nome_sito,
            ip=ip,
            config=config,
            connection_method=connection_method
        )

        return jsonify({
            'success': True,
            **result,
        })

    except Exception as e:
        logger.error(f"Backup failed for {ip}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'ip': ip,
        }), 500


@bp.route('/api/backup/subnet', methods=['POST'])
def create_subnet_backup():
    """
    Create backups for all devices in a subnet.

    Request JSON:
        - subnet: CIDR notation (e.g., 10.1.4.0/24)
        - username: SSH username
        - password: SSH password
        - core_only: Only backup .251 addresses (default: true)

    Returns:
        JSON with results for each device
    """
    data = request.get_json() or {}

    subnet_str = data.get('subnet')
    username = data.get('username')
    password = data.get('password')
    core_only = data.get('core_only', True)

    if not subnet_str:
        return jsonify({
            'success': False,
            'error': 'Subnet is required',
        }), 400

    if not username or not password:
        return jsonify({
            'success': False,
            'error': 'Username and password are required',
        }), 400

    try:
        network = ipaddress.ip_network(subnet_str, strict=False)
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid subnet: {e}',
        }), 400

    # Generate list of IPs to backup
    if core_only:
        # Only .251 (core switch)
        base = str(network.network_address).rsplit('.', 1)[0]
        ips = [f"{base}.251"]
    else:
        # All hosts in subnet (skip network and broadcast)
        ips = [str(ip) for ip in network.hosts()]

    results = []
    failed = []

    def backup_single(ip):
        """Backup single device"""
        try:
            with SSHManager(ip, username, password) as ssh:
                config = ssh.get_current_configuration()
                connection_method = ssh.connection_method

            result = save_backup(
                sito=ip,
                nome_sito='',
                ip=ip,
                config=config,
                connection_method=connection_method
            )
            return {'success': True, 'ip': ip, **result}
        except Exception as e:
            return {'success': False, 'ip': ip, 'error': str(e)}

    # Parallel execution with max 4 workers
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(backup_single, ip): ip for ip in ips}

        for future in as_completed(futures):
            result = future.result()
            if result['success']:
                results.append(result)
            else:
                failed.append(result)

    return jsonify({
        'success': True,
        'total': len(ips),
        'successful': len(results),
        'failed_count': len(failed),
        'results': results,
        'failed': failed,
    })


@bp.route('/api/backups', methods=['GET'])
def list_backups():
    """
    Get list of backups with optional filtering.

    Query params:
        - sito: Filter by site ID
        - ip: Filter by IP
        - limit: Max results (default 50)
        - offset: Pagination offset
    """
    sito = request.args.get('sito')
    ip = request.args.get('ip')
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))

    backups = database.get_backups_list(sito=sito, ip=ip, limit=limit, offset=offset)
    total = database.get_backups_count(sito=sito, ip=ip)

    return jsonify({
        'success': True,
        'backups': backups,
        'total': total,
        'limit': limit,
        'offset': offset,
    })


@bp.route('/api/backups/<int:backup_id>', methods=['GET'])
def get_backup(backup_id):
    """
    Get backup details by ID.

    Query params:
        - include_config: Include full config content (default false)
    """
    include_config = request.args.get('include_config', 'false').lower() == 'true'

    backup = database.get_backup_by_id(backup_id)

    if not backup:
        return jsonify({
            'success': False,
            'error': 'Backup not found',
        }), 404

    result = {
        'success': True,
        'backup': backup,
    }

    if include_config:
        config = read_backup_file(backup['filename'])
        result['config'] = config

    return jsonify(result)


@bp.route('/api/diff/<int:backup_id_1>/<int:backup_id_2>', methods=['GET'])
def get_diff(backup_id_1, backup_id_2):
    """
    Get diff between two specific backups.
    """
    result = get_diff_between_backups(backup_id_1, backup_id_2)

    if 'error' in result:
        return jsonify({
            'success': False,
            **result,
        }), 404

    return jsonify({
        'success': True,
        **result,
    })


@bp.route('/api/diff/latest/<sito>', methods=['GET'])
def get_latest_site_diff(sito):
    """
    Get diff between the two most recent backups for a site.
    """
    result = get_latest_diff(sito=sito)

    if 'error' in result:
        return jsonify({
            'success': False,
            **result,
        }), 404

    return jsonify({
        'success': True,
        **result,
    })


@bp.route('/api/backups/<int:backup_id>/download', methods=['GET'])
def download_backup(backup_id):
    """
    Download backup file.
    """
    backup = database.get_backup_by_id(backup_id)

    if not backup:
        return jsonify({
            'success': False,
            'error': 'Backup not found',
        }), 404

    # Get directory and filename
    import os
    filepath = os.path.join(BACKUPS_DIR, backup['filename'])
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)

    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name=f"{backup['sito']}_{filename}"
    )


@bp.route('/api/backup/discover-and-backup', methods=['POST'])
def discover_and_backup():
    """
    Discover devices in subnet then backup configurations.

    Workflow:
    1. Call discovery API to find devices via SNMP
    2. Classify devices (Core .251 vs L2)
    3. Apply correct credentials per device type
    4. Execute parallel backups

    Request JSON:
        - subnet: CIDR notation (e.g., 10.10.4.0/24)
        - sito: Site ID for credential lookup (optional)
        - username: L2 switch username (if no sito)
        - password: L2 switch password (if no sito)
        - username_core: Core switch username (optional)
        - password_core: Core switch password (optional)
        - backup_core_only: Only backup core switches (default: false)
        - backup_l2_only: Only backup L2 switches (default: false)

    Returns:
        JSON with discovery results and backup status per device
    """
    data = request.get_json() or {}

    subnet = data.get('subnet')
    sito = data.get('sito')

    # Validate subnet
    if not subnet:
        return jsonify({'success': False, 'error': 'Subnet is required'}), 400

    try:
        network = ipaddress.ip_network(subnet, strict=False)
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid subnet: {e}'}), 400

    # Get credentials based on source
    all_credentials = []  # List of fallback credentials
    if sito:
        site = get_site_by_id(sito)
        if not site:
            return jsonify({'success': False, 'error': f'Site not found: {sito}'}), 404

        creds_l2 = {
            'username': site['utente'],
            'password': site['password']
        }
        creds_core = {
            'username': site['utente_core'] or site['utente'],
            'password': site['password_core'] or site['password']
        }
        nome_sito = site['nome']

        # Get all credential sets for fallback
        all_credentials = get_all_credentials_for_site(sito)
        logger.info(f"Found {len(all_credentials)} credential sets for site {sito}")
    else:
        creds_l2 = {
            'username': data.get('username'),
            'password': data.get('password')
        }
        creds_core = {
            'username': data.get('username_core') or data.get('username'),
            'password': data.get('password_core') or data.get('password')
        }
        nome_sito = data.get('nome_sito', '')

    # Validate credentials
    if not creds_l2.get('username') or not creds_l2.get('password'):
        return jsonify({
            'success': False,
            'error': 'Username and password are required'
        }), 400

    # Step 1: Discovery
    logger.info(f"Starting discovery for subnet: {subnet}")
    discovery_result = call_discovery_api(subnet)

    if not discovery_result.get('success'):
        return jsonify({
            'success': False,
            'error': 'Discovery failed',
            'details': discovery_result.get('error', 'Unknown error')
        }), 500

    devices = discovery_result.get('devices', [])
    total_scanned = discovery_result.get('total_scanned', 0)

    if not devices:
        return jsonify({
            'success': True,
            'message': 'No devices found in subnet',
            'discovery': {
                'total_scanned': total_scanned,
                'devices_found': 0
            }
        })

    # Step 2: Filter and classify devices
    backup_core_only = data.get('backup_core_only', False)
    backup_l2_only = data.get('backup_l2_only', False)

    devices_to_backup = []
    for device in devices:
        ip = device.get('ip', '')
        is_core = ip.endswith('.251')

        # Apply filters
        if backup_core_only and not is_core:
            continue
        if backup_l2_only and is_core:
            continue

        devices_to_backup.append({
            'ip': ip,
            'hostname': device.get('hostname', ''),
            'model': device.get('model', ''),
            'type': 'core' if is_core else 'l2',
            'credentials': creds_core if is_core else creds_l2,
            'fallback_credentials': all_credentials if not is_core else []
        })

    if not devices_to_backup:
        return jsonify({
            'success': True,
            'message': 'No devices match the filter criteria',
            'discovery': {
                'total_scanned': total_scanned,
                'devices_found': len(devices),
                'devices_filtered': 0
            }
        })

    # Step 3: Parallel backup
    logger.info(f"Starting backup for {len(devices_to_backup)} devices")
    results = []
    failed = []

    def backup_device(device):
        """Backup single device with appropriate credentials and fallback support"""
        device_ip = device['ip']
        primary_creds = device['credentials']
        fallback_list = device.get('fallback_credentials', [])

        # Build list of credentials to try (primary first, then fallbacks)
        credentials_to_try = [primary_creds]
        for fb in fallback_list:
            cred = {'username': fb['username'], 'password': fb['password']}
            # Avoid duplicates
            if cred not in credentials_to_try:
                credentials_to_try.append(cred)

        last_error = None
        for idx, creds in enumerate(credentials_to_try):
            try:
                with SSHManager(
                    device_ip,
                    creds['username'],
                    creds['password']
                ) as ssh:
                    config = ssh.get_current_configuration()
                    connection_method = ssh.connection_method

                result = save_backup(
                    sito=sito or device_ip,
                    nome_sito=nome_sito,
                    ip=device_ip,
                    config=config,
                    connection_method=connection_method
                )

                if idx > 0:
                    logger.info(f"Backup successful for {device_ip} (fallback credential #{idx})")
                else:
                    logger.info(f"Backup successful for {device_ip}")

                return {
                    'success': True,
                    'ip': device_ip,
                    'hostname': device.get('hostname', ''),
                    'type': device['type'],
                    'backup_id': result.get('id'),
                    'has_changes': result.get('has_changes', False),
                    'is_duplicate': result.get('is_duplicate', False),
                    'connection_method': connection_method,
                    'used_fallback': idx > 0
                }
            except Exception as e:
                last_error = str(e)
                # Only try fallback for authentication errors
                if 'Authentication failed' in str(e) or 'Invalid username' in str(e):
                    if idx < len(credentials_to_try) - 1:
                        logger.debug(f"Auth failed for {device_ip} with cred #{idx}, trying fallback")
                        continue
                # For non-auth errors, don't try fallback
                break

        logger.error(f"Backup failed for {device_ip}: {last_error}")
        return {
            'success': False,
            'ip': device_ip,
            'hostname': device.get('hostname', ''),
            'type': device['type'],
            'error': last_error
        }

    # Execute backups in parallel (max 4 workers to avoid overloading)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(backup_device, d): d for d in devices_to_backup}

        for future in as_completed(futures):
            result = future.result()
            if result['success']:
                results.append(result)
            else:
                failed.append(result)

    # Summary
    logger.info(f"Subnet backup completed: {len(results)} success, {len(failed)} failed")

    return jsonify({
        'success': True,
        'discovery': {
            'total_scanned': total_scanned,
            'devices_found': len(devices),
            'devices_to_backup': len(devices_to_backup)
        },
        'backup': {
            'total': len(devices_to_backup),
            'successful': len(results),
            'failed_count': len(failed),
            'results': results,
            'failed': failed
        }
    })


def call_discovery_api(subnet):
    """
    Call the existing Huawei Network Discovery API.

    Args:
        subnet: Network in CIDR notation

    Returns:
        dict: Discovery results with devices list
    """
    try:
        # Call discovery API (runs on same server via nginx)
        response = requests.post(
            'http://localhost/api/discover',
            json={'network': subnet, 'sync': True},
            timeout=180  # Discovery can take 2-3 minutes for /24
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                'success': False,
                'error': f'Discovery API returned {response.status_code}'
            }

    except requests.exceptions.Timeout:
        logger.error(f"Discovery timeout for subnet {subnet}")
        return {'success': False, 'error': 'Discovery timeout'}
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Cannot connect to discovery API: {e}")
        return {'success': False, 'error': 'Cannot connect to discovery API'}
    except Exception as e:
        logger.error(f"Discovery API call failed: {e}")
        return {'success': False, 'error': str(e)}


@bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'service': 'config-backup',
    })
