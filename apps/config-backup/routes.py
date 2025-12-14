"""Flask routes for Config Backup API"""
from flask import Blueprint, request, jsonify, render_template, send_from_directory
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress

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


@bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'service': 'config-backup',
    })
