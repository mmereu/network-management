"""SQLite database manager for backup metadata"""
import sqlite3
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Database path in app directory
DB_PATH = os.path.join(os.path.dirname(__file__), 'config_backup.db')


def get_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sito TEXT NOT NULL,
            nome_sito TEXT,
            ip TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            filename TEXT NOT NULL,
            hash_config TEXT NOT NULL,
            config_size INTEGER,
            connection_method TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create indexes for common queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_backups_sito ON backups(sito)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_backups_ip ON backups(ip)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_backups_timestamp ON backups(timestamp DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_backups_hash ON backups(hash_config)')

    conn.commit()
    conn.close()
    logger.info("Database initialized")


def insert_backup(sito, nome_sito, ip, filename, hash_config, config_size, connection_method):
    """
    Insert new backup record.

    Returns:
        int: ID of inserted record
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO backups (sito, nome_sito, ip, filename, hash_config, config_size, connection_method)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (sito, nome_sito, ip, filename, hash_config, config_size, connection_method))

    backup_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Inserted backup record: id={backup_id}, sito={sito}, ip={ip}")
    return backup_id


def get_backup_by_id(backup_id):
    """Get backup record by ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM backups WHERE id = ?', (backup_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_latest_backup(sito=None, ip=None):
    """
    Get most recent backup for a site or IP.

    Args:
        sito: Site ID (optional)
        ip: IP address (optional)

    Returns:
        dict: Backup record or None
    """
    conn = get_connection()
    cursor = conn.cursor()

    if sito:
        cursor.execute('''
            SELECT * FROM backups
            WHERE sito = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (sito,))
    elif ip:
        cursor.execute('''
            SELECT * FROM backups
            WHERE ip = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (ip,))
    else:
        return None

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_previous_backup(sito=None, ip=None, exclude_id=None):
    """
    Get the backup before the most recent one.

    Args:
        sito: Site ID (optional)
        ip: IP address (optional)
        exclude_id: ID to exclude (usually current backup)

    Returns:
        dict: Previous backup record or None
    """
    conn = get_connection()
    cursor = conn.cursor()

    if sito:
        if exclude_id:
            cursor.execute('''
                SELECT * FROM backups
                WHERE sito = ? AND id != ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (sito, exclude_id))
        else:
            cursor.execute('''
                SELECT * FROM backups
                WHERE sito = ?
                ORDER BY timestamp DESC
                LIMIT 1 OFFSET 1
            ''', (sito,))
    elif ip:
        if exclude_id:
            cursor.execute('''
                SELECT * FROM backups
                WHERE ip = ? AND id != ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (ip, exclude_id))
        else:
            cursor.execute('''
                SELECT * FROM backups
                WHERE ip = ?
                ORDER BY timestamp DESC
                LIMIT 1 OFFSET 1
            ''', (ip,))
    else:
        return None

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_backups_list(sito=None, ip=None, limit=50, offset=0):
    """
    Get list of backups with optional filtering.

    Returns:
        list[dict]: List of backup records
    """
    conn = get_connection()
    cursor = conn.cursor()

    if sito:
        cursor.execute('''
            SELECT * FROM backups
            WHERE sito = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (sito, limit, offset))
    elif ip:
        cursor.execute('''
            SELECT * FROM backups
            WHERE ip = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (ip, limit, offset))
    else:
        cursor.execute('''
            SELECT * FROM backups
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_backups_count(sito=None, ip=None):
    """Get total count of backups"""
    conn = get_connection()
    cursor = conn.cursor()

    if sito:
        cursor.execute('SELECT COUNT(*) as count FROM backups WHERE sito = ?', (sito,))
    elif ip:
        cursor.execute('SELECT COUNT(*) as count FROM backups WHERE ip = ?', (ip,))
    else:
        cursor.execute('SELECT COUNT(*) as count FROM backups')

    row = cursor.fetchone()
    conn.close()

    return row['count'] if row else 0


def check_config_exists(hash_config, sito=None, ip=None):
    """
    Check if a configuration with same hash already exists.

    Returns:
        dict: Existing backup record if found, None otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()

    if sito:
        cursor.execute('''
            SELECT * FROM backups
            WHERE hash_config = ? AND sito = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (hash_config, sito))
    elif ip:
        cursor.execute('''
            SELECT * FROM backups
            WHERE hash_config = ? AND ip = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (hash_config, ip))
    else:
        cursor.execute('''
            SELECT * FROM backups
            WHERE hash_config = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (hash_config,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def delete_backup(backup_id):
    """Delete backup record by ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM backups WHERE id = ?', (backup_id,))
    deleted = cursor.rowcount

    conn.commit()
    conn.close()

    return deleted > 0
