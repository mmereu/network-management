#!/usr/bin/env python3
"""
Scheduled Backup Script - Backup all sites automatically

This script is designed to be run via cron at 2:00 AM daily.
It iterates through all sites in Pdv.CSV and triggers subnet backups.

Usage:
    python3 scheduled_backup.py [--dry-run] [--site SITE_ID] [--no-email]

Cron entry (2:00 AM daily):
    0 2 * * * cd /var/www/html/apps/config-backup && /usr/bin/python3 scheduled_backup.py >> /var/log/config-backup-scheduled.log 2>&1

Environment variables for email:
    SMTP_SERVER: SMTP server hostname (default: smtp.office365.com)
    SMTP_PORT: SMTP port (default: 587)
    SMTP_USER: SMTP username/email for authentication
    SMTP_PASSWORD: SMTP password
    SMTP_FROM: From email address (default: same as SMTP_USER)
    SMTP_TO: Recipient email address (default: admin@example.com)
    SMTP_TLS: Use TLS (default: true)
"""

import os
import sys
import json
import logging
import argparse
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from time import sleep

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from csv_parser import parse_pdv_csv

# Configuration
API_BASE_URL = os.environ.get('BACKUP_API_URL', 'http://localhost:5003')
REQUEST_TIMEOUT = 600  # 10 minutes per site
DELAY_BETWEEN_SITES = 5  # seconds

# Email Configuration
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'localhost')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '25'))
SMTP_FROM = os.environ.get('SMTP_FROM', 'config-backup@example.com')
SMTP_TO = os.environ.get('SMTP_TO', 'admin@example.com')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def send_email_report(summary, results):
    """
    Send email report with backup summary.

    Args:
        summary: dict with backup summary stats
        results: list of per-site results
    """
    if not SMTP_SERVER:
        logger.warning("SMTP_SERVER not configured, skipping email")
        return False

    # Determine status
    all_success = summary['sites_failed'] == 0
    status_emoji = "✅" if all_success else "⚠️"
    status_text = "COMPLETATO" if all_success else "COMPLETATO CON ERRORI"

    # Build HTML email
    subject = f"{status_emoji} Config Backup Report - {summary['sites_successful']}/{summary['sites_total']} siti OK"

    # Build failed sites list
    failed_sites_html = ""
    if summary['sites_failed'] > 0:
        failed_sites_html = "<h3 style='color: #dc3545;'>Siti con errori:</h3><ul>"
        for r in results:
            if not r.get('success'):
                failed_sites_html += f"<li><strong>{r['nome']}</strong> ({r['sito']}): {r.get('error', 'Unknown')}</li>"
        failed_sites_html += "</ul>"

    # Build successful sites summary
    success_sites_html = "<h3 style='color: #28a745;'>Siti completati:</h3><table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>"
    success_sites_html += "<tr style='background: #f8f9fa;'><th>Sito</th><th>Dispositivi</th><th>OK</th><th>Falliti</th></tr>"
    for r in results:
        if r.get('success') and not r.get('dry_run'):
            row_style = "" if r.get('failed', 0) == 0 else "background: #fff3cd;"
            success_sites_html += f"<tr style='{row_style}'><td>{r['nome']}</td><td>{r.get('total', 0)}</td><td>{r.get('successful', 0)}</td><td>{r.get('failed', 0)}</td></tr>"
    success_sites_html += "</table>"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h1 style="color: {'#28a745' if all_success else '#dc3545'};">{status_emoji} Backup {status_text}</h1>

        <h2>Riepilogo</h2>
        <table border="0" cellpadding="8" style="background: #f8f9fa; border-radius: 8px;">
            <tr><td><strong>Data:</strong></td><td>{summary['start_time'][:19].replace('T', ' ')}</td></tr>
            <tr><td><strong>Durata:</strong></td><td>{int(summary['duration_seconds'] // 60)} minuti {int(summary['duration_seconds'] % 60)} secondi</td></tr>
            <tr><td><strong>Siti totali:</strong></td><td>{summary['sites_total']}</td></tr>
            <tr><td><strong>Siti OK:</strong></td><td style="color: #28a745;">{summary['sites_successful']}</td></tr>
            <tr><td><strong>Siti falliti:</strong></td><td style="color: {'#dc3545' if summary['sites_failed'] > 0 else '#28a745'};">{summary['sites_failed']}</td></tr>
            <tr><td><strong>Dispositivi totali:</strong></td><td>{summary['devices_total']}</td></tr>
            <tr><td><strong>Dispositivi OK:</strong></td><td style="color: #28a745;">{summary['devices_successful']}</td></tr>
            <tr><td><strong>Dispositivi falliti:</strong></td><td style="color: {'#dc3545' if summary['devices_failed'] > 0 else '#28a745'};">{summary['devices_failed']}</td></tr>
        </table>

        {failed_sites_html}

        {success_sites_html}

        <hr>
        <p style="color: #6c757d; font-size: 12px;">
            Questo report è stato generato automaticamente da Config Backup.<br>
            Log: /var/log/config-backup-scheduled.log
        </p>
    </body>
    </html>
    """

    # Create message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SMTP_FROM
    msg['To'] = SMTP_TO

    # Plain text fallback
    text_body = f"""
Config Backup Report - {status_text}

Data: {summary['start_time'][:19]}
Durata: {int(summary['duration_seconds'] // 60)}m {int(summary['duration_seconds'] % 60)}s

Siti: {summary['sites_successful']}/{summary['sites_total']} OK, {summary['sites_failed']} falliti
Dispositivi: {summary['devices_successful']}/{summary['devices_total']} OK, {summary['devices_failed']} falliti
"""

    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    try:
        logger.info(f"Sending email report to {SMTP_TO} via {SMTP_SERVER}:{SMTP_PORT}")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.sendmail(SMTP_FROM, SMTP_TO.split(','), msg.as_string())
        logger.info("Email report sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def backup_site(site, dry_run=False):
    """
    Trigger backup for a single site.

    Args:
        site: Site dictionary from CSV
        dry_run: If True, only log what would be done

    Returns:
        dict with success status and details
    """
    sito_id = site['sito']
    nome = site['nome']
    network = site['network']

    logger.info(f"[{sito_id}] Starting backup for {nome} ({network})")

    if not network:
        logger.warning(f"[{sito_id}] No network defined, skipping")
        return {
            'success': False,
            'sito': sito_id,
            'nome': nome,
            'error': 'No network defined'
        }

    if dry_run:
        logger.info(f"[{sito_id}] DRY RUN - Would backup subnet {network}")
        return {
            'success': True,
            'sito': sito_id,
            'nome': nome,
            'dry_run': True
        }

    # Prepare request payload
    payload = {
        'subnet': network,
        'sito': sito_id
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/backup/discover-and-backup",
            json=payload,
            timeout=REQUEST_TIMEOUT
        )

        result = response.json()

        if result.get('success'):
            # Extract stats from correct response structure
            backup_data = result.get('backup', {})
            backup_results = backup_data.get('results', [])
            backup_failed = backup_data.get('failed', [])

            successful = len([r for r in backup_results if r.get('success')])
            failed = len(backup_failed)
            total = successful + failed

            # Also count from discovery if available
            discovery = result.get('discovery', {})
            devices_found = discovery.get('devices_found', total)

            logger.info(f"[{sito_id}] Backup completed: {successful}/{devices_found} successful, {failed} failed")

            return {
                'success': True,
                'sito': sito_id,
                'nome': nome,
                'total': devices_found,
                'successful': successful,
                'failed': failed,
                'devices': backup_results + backup_failed
            }
        else:
            error = result.get('error', 'Unknown error')
            logger.error(f"[{sito_id}] Backup failed: {error}")
            return {
                'success': False,
                'sito': sito_id,
                'nome': nome,
                'error': error
            }

    except requests.exceptions.Timeout:
        logger.error(f"[{sito_id}] Timeout after {REQUEST_TIMEOUT}s")
        return {
            'success': False,
            'sito': sito_id,
            'nome': nome,
            'error': 'Timeout'
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"[{sito_id}] Request error: {e}")
        return {
            'success': False,
            'sito': sito_id,
            'nome': nome,
            'error': str(e)
        }
    except Exception as e:
        logger.error(f"[{sito_id}] Unexpected error: {e}")
        return {
            'success': False,
            'sito': sito_id,
            'nome': nome,
            'error': str(e)
        }


def run_scheduled_backup(dry_run=False, site_filter=None, send_email=True):
    """
    Run backup for all sites or a specific site.

    Args:
        dry_run: If True, only log what would be done
        site_filter: If set, only backup this site ID
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"SCHEDULED BACKUP STARTED at {start_time}")
    logger.info("=" * 60)

    # Load sites from CSV
    sites = parse_pdv_csv()

    if not sites:
        logger.error("No sites found in CSV")
        return

    # Filter sites if requested
    if site_filter:
        sites = [s for s in sites if s['sito'] == site_filter]
        if not sites:
            logger.error(f"Site {site_filter} not found")
            return

    logger.info(f"Found {len(sites)} sites to backup")

    results = []

    for i, site in enumerate(sites, 1):
        logger.info(f"--- Site {i}/{len(sites)} ---")

        result = backup_site(site, dry_run=dry_run)
        results.append(result)

        # Delay between sites (except for last one)
        if i < len(sites) and not dry_run:
            logger.info(f"Waiting {DELAY_BETWEEN_SITES}s before next site...")
            sleep(DELAY_BETWEEN_SITES)

    # Summary
    end_time = datetime.now()
    duration = end_time - start_time

    successful_sites = sum(1 for r in results if r.get('success'))
    failed_sites = sum(1 for r in results if not r.get('success'))
    total_devices = sum(r.get('total', 0) for r in results)
    total_successful = sum(r.get('successful', 0) for r in results)
    total_failed_devices = sum(r.get('failed', 0) for r in results)

    logger.info("=" * 60)
    logger.info("SCHEDULED BACKUP COMPLETED")
    logger.info("=" * 60)
    logger.info(f"Duration: {duration}")
    logger.info(f"Sites: {successful_sites} successful, {failed_sites} failed")
    logger.info(f"Devices: {total_successful}/{total_devices} backed up, {total_failed_devices} failed")

    # Log failed sites
    if failed_sites > 0:
        logger.warning("Failed sites:")
        for r in results:
            if not r.get('success'):
                logger.warning(f"  - {r['nome']} ({r['sito']}): {r.get('error', 'Unknown')}")

    # Build summary dict
    summary = {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'duration_seconds': duration.total_seconds(),
        'sites_total': len(sites),
        'sites_successful': successful_sites,
        'sites_failed': failed_sites,
        'devices_total': total_devices,
        'devices_successful': total_successful,
        'devices_failed': total_failed_devices,
        'results': results
    }

    # Write summary to JSON file
    summary_file = f"/tmp/backup_summary_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Summary saved to {summary_file}")
    except Exception as e:
        logger.warning(f"Could not save summary: {e}")

    # Send email report
    if send_email and not dry_run:
        send_email_report(summary, results)

    return summary


def main():
    parser = argparse.ArgumentParser(description='Scheduled backup for all sites')
    parser.add_argument('--dry-run', action='store_true',
                        help='Only log what would be done, no actual backups')
    parser.add_argument('--site', type=str,
                        help='Only backup specific site ID')
    parser.add_argument('--no-email', action='store_true',
                        help='Do not send email report')

    args = parser.parse_args()

    run_scheduled_backup(dry_run=args.dry_run, site_filter=args.site, send_email=not args.no_email)


if __name__ == '__main__':
    main()
