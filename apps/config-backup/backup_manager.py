"""Backup manager for saving configurations and calculating diffs"""
import os
import hashlib
import difflib
from datetime import datetime
import logging

# Support both module and standalone execution
try:
    from . import database
except ImportError:
    import database

logger = logging.getLogger(__name__)

# Backup directory path
BACKUPS_DIR = os.path.join(os.path.dirname(__file__), 'backups')


def ensure_backup_dir(sito):
    """Ensure backup directory exists for a site"""
    site_dir = os.path.join(BACKUPS_DIR, _sanitize_dirname(sito))
    os.makedirs(site_dir, exist_ok=True)
    return site_dir


def _sanitize_dirname(name):
    """Sanitize directory name (remove invalid chars)"""
    # Replace spaces and special chars
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()


def hash_config(config):
    """
    Calculate SHA256 hash of configuration.

    Args:
        config: Configuration string

    Returns:
        str: SHA256 hash hex digest
    """
    return hashlib.sha256(config.encode('utf-8')).hexdigest()


def save_backup(sito, nome_sito, ip, config, connection_method):
    """
    Save configuration backup to file and database.

    Args:
        sito: Site ID
        nome_sito: Site name
        ip: Device IP address
        config: Configuration content
        connection_method: SSH or Telnet

    Returns:
        dict: Backup info with id, filename, hash, has_changes, diff
    """
    # Calculate hash
    config_hash = hash_config(config)

    # Check if identical config already exists
    existing = database.check_config_exists(config_hash, sito=sito)
    if existing:
        logger.info(f"Identical configuration already exists: backup_id={existing['id']}")
        return {
            'id': existing['id'],
            'filename': existing['filename'],
            'hash': config_hash,
            'is_duplicate': True,
            'has_changes': False,
            'message': 'Configuration unchanged since last backup',
            'existing_backup': existing,
        }

    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{timestamp}.cfg"

    # Ensure directory exists
    site_dir = ensure_backup_dir(f"{sito}_{nome_sito}" if nome_sito else sito)
    filepath = os.path.join(site_dir, filename)

    # Write config to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(config)

    config_size = len(config)

    # Get relative path for database
    rel_filepath = os.path.relpath(filepath, BACKUPS_DIR)

    # Insert into database
    backup_id = database.insert_backup(
        sito=sito,
        nome_sito=nome_sito,
        ip=ip,
        filename=rel_filepath,
        hash_config=config_hash,
        config_size=config_size,
        connection_method=connection_method
    )

    logger.info(f"Saved backup: id={backup_id}, file={rel_filepath}")

    # Get previous backup for diff
    previous = database.get_previous_backup(sito=sito, exclude_id=backup_id)

    result = {
        'id': backup_id,
        'filename': rel_filepath,
        'filepath': filepath,
        'hash': config_hash,
        'size': config_size,
        'is_duplicate': False,
        'has_changes': previous is not None,
        'connection_method': connection_method,
    }

    # Calculate diff if previous backup exists
    if previous:
        previous_config = read_backup_file(previous['filename'])
        if previous_config:
            diff_result = calculate_diff(previous_config, config)
            result['diff'] = diff_result
            result['previous_backup'] = {
                'id': previous['id'],
                'timestamp': previous['timestamp'],
                'filename': previous['filename'],
            }
            result['has_changes'] = diff_result['has_changes']

    return result


def read_backup_file(filename):
    """
    Read backup file content.

    Args:
        filename: Relative path from backups directory

    Returns:
        str: File content or None if not found
    """
    filepath = os.path.join(BACKUPS_DIR, filename)

    if not os.path.exists(filepath):
        logger.warning(f"Backup file not found: {filepath}")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading backup file: {e}")
        return None


def calculate_diff(old_config, new_config):
    """
    Calculate differences between two configurations.

    Args:
        old_config: Previous configuration content
        new_config: Current configuration content

    Returns:
        dict: Diff result with added, removed, and statistics
    """
    old_lines = old_config.splitlines(keepends=False)
    new_lines = new_config.splitlines(keepends=False)

    # Use difflib for detailed comparison
    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile='previous',
        tofile='current',
        lineterm=''
    ))

    # Parse diff output
    added = []
    removed = []
    context = []

    for line in diff:
        if line.startswith('+++') or line.startswith('---'):
            continue
        elif line.startswith('@@'):
            context.append(line)
        elif line.startswith('+'):
            added.append(line[1:])  # Remove + prefix
        elif line.startswith('-'):
            removed.append(line[1:])  # Remove - prefix

    # Create side-by-side diff for UI
    side_by_side = create_side_by_side_diff(old_lines, new_lines)

    return {
        'has_changes': len(added) > 0 or len(removed) > 0,
        'added_count': len(added),
        'removed_count': len(removed),
        'added_lines': added,
        'removed_lines': removed,
        'unified_diff': diff,
        'side_by_side': side_by_side,
        'old_line_count': len(old_lines),
        'new_line_count': len(new_lines),
    }


def create_side_by_side_diff(old_lines, new_lines):
    """
    Create side-by-side diff for visual display.

    Returns:
        list[dict]: List of diff entries with left/right content and status
    """
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for i, j in zip(range(i1, i2), range(j1, j2)):
                result.append({
                    'status': 'unchanged',
                    'left_num': i + 1,
                    'left': old_lines[i],
                    'right_num': j + 1,
                    'right': new_lines[j],
                })
        elif tag == 'replace':
            # Handle replacements
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                left_idx = i1 + k if i1 + k < i2 else None
                right_idx = j1 + k if j1 + k < j2 else None

                result.append({
                    'status': 'modified',
                    'left_num': left_idx + 1 if left_idx is not None else None,
                    'left': old_lines[left_idx] if left_idx is not None else '',
                    'right_num': right_idx + 1 if right_idx is not None else None,
                    'right': new_lines[right_idx] if right_idx is not None else '',
                })
        elif tag == 'delete':
            for i in range(i1, i2):
                result.append({
                    'status': 'removed',
                    'left_num': i + 1,
                    'left': old_lines[i],
                    'right_num': None,
                    'right': '',
                })
        elif tag == 'insert':
            for j in range(j1, j2):
                result.append({
                    'status': 'added',
                    'left_num': None,
                    'left': '',
                    'right_num': j + 1,
                    'right': new_lines[j],
                })

    return result


def get_diff_between_backups(backup_id_1, backup_id_2):
    """
    Calculate diff between two specific backups.

    Args:
        backup_id_1: First backup ID (older)
        backup_id_2: Second backup ID (newer)

    Returns:
        dict: Diff result or error
    """
    backup1 = database.get_backup_by_id(backup_id_1)
    backup2 = database.get_backup_by_id(backup_id_2)

    if not backup1:
        return {'error': f'Backup {backup_id_1} not found'}
    if not backup2:
        return {'error': f'Backup {backup_id_2} not found'}

    config1 = read_backup_file(backup1['filename'])
    config2 = read_backup_file(backup2['filename'])

    if not config1:
        return {'error': f'Cannot read backup file: {backup1["filename"]}'}
    if not config2:
        return {'error': f'Cannot read backup file: {backup2["filename"]}'}

    diff_result = calculate_diff(config1, config2)

    return {
        'backup_1': {
            'id': backup1['id'],
            'timestamp': backup1['timestamp'],
            'sito': backup1['sito'],
        },
        'backup_2': {
            'id': backup2['id'],
            'timestamp': backup2['timestamp'],
            'sito': backup2['sito'],
        },
        **diff_result,
    }


def get_latest_diff(sito=None, ip=None):
    """
    Get diff between the two most recent backups.

    Returns:
        dict: Diff result or message if no previous backup
    """
    latest = database.get_latest_backup(sito=sito, ip=ip)

    if not latest:
        return {'error': 'No backups found'}

    previous = database.get_previous_backup(sito=sito, ip=ip, exclude_id=latest['id'])

    if not previous:
        return {
            'message': 'Only one backup exists - no diff available',
            'latest': latest,
        }

    return get_diff_between_backups(previous['id'], latest['id'])
