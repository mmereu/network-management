"""Parser for Pdv.CSV file containing site credentials"""
import csv
import os
import logging

logger = logging.getLogger(__name__)

# Path to Pdv.CSV in project root
DEFAULT_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'Pdv.CSV')


def parse_pdv_csv(filepath=None):
    """
    Parse Pdv.CSV file and return list of site dictionaries.

    CSV Format (semicolon separated):
    sito;Nome;Network;utente;password;Switch CORE;utente Core;password core

    Returns:
        list[dict]: List of site configurations with keys:
            - sito: Site ID
            - nome: Site name
            - network: Network CIDR (e.g., 10.1.4.0/24)
            - utente: Local switch username
            - password: Local switch password
            - switch_core_ip: Core switch IP
            - utente_core: Core switch username
            - password_core: Core switch password
    """
    if filepath is None:
        filepath = DEFAULT_CSV_PATH

    sites = []

    if not os.path.exists(filepath):
        logger.warning(f"CSV file not found: {filepath}")
        return sites

    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            # Use semicolon as delimiter
            reader = csv.DictReader(f, delimiter=';')

            for row in reader:
                # Skip empty rows or header-like rows
                sito = row.get('sito', '').strip()
                if not sito or sito.upper() == 'SITO':
                    continue

                # Skip CORE fallback row
                if sito.upper() == 'CORE':
                    continue

                # Clean password fields (handle escaped quotes)
                password = row.get('password', '').strip()
                password_core = row.get('password core', '').strip()

                # Remove surrounding quotes and unescape double quotes
                password = _clean_password(password)
                password_core = _clean_password(password_core)

                site = {
                    'sito': sito,
                    'nome': row.get('Nome', '').strip(),
                    'network': row.get('Network', '').strip(),
                    'utente': row.get('utente', '').strip(),
                    'password': password,
                    'switch_core_ip': row.get('Switch CORE', '').strip(),
                    'utente_core': row.get('utente Core', '').strip(),
                    'password_core': password_core,
                }

                sites.append(site)

        logger.info(f"Loaded {len(sites)} sites from CSV")

    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")

    return sites


def _clean_password(password):
    """Clean password field from CSV escaping.

    Note: Python's csv module already handles quote unescaping,
    so we only need to handle edge cases where quotes might remain.
    """
    if not password:
        return password

    # Only remove surrounding quotes if they exist (shouldn't happen with csv module)
    if password.startswith('"') and password.endswith('"'):
        password = password[1:-1]

    # DO NOT unescape double quotes - csv module already does this
    # The password may legitimately contain "" as part of the actual password

    return password


def get_site_by_id(sito_id, filepath=None):
    """Get a specific site by its ID (returns first match)"""
    sites = parse_pdv_csv(filepath)
    for site in sites:
        if site['sito'] == str(sito_id):
            return site
    return None


def get_all_credentials_for_site(sito_id, filepath=None):
    """
    Get all credential sets for a site ID.

    Returns a list of unique credential combinations for sites with multiple entries.
    Useful for credential fallback when some switches use different credentials.

    Returns:
        list[dict]: List of credential sets with keys:
            - username: L2 switch username
            - password: L2 switch password
            - username_core: Core switch username
            - password_core: Core switch password
    """
    sites = parse_pdv_csv(filepath)
    credentials = []
    seen = set()

    for site in sites:
        if site['sito'] == str(sito_id):
            # Create a unique key for this credential set
            cred_key = (site['utente'], site['password'])
            if cred_key not in seen:
                seen.add(cred_key)
                credentials.append({
                    'username': site['utente'],
                    'password': site['password'],
                    'username_core': site['utente_core'] or site['utente'],
                    'password_core': site['password_core'] or site['password'],
                })

    return credentials


def get_site_by_name(nome, filepath=None):
    """Get a specific site by its name"""
    sites = parse_pdv_csv(filepath)
    for site in sites:
        if site['nome'].lower() == nome.lower():
            return site
    return None


def get_sites_dropdown():
    """Get sites formatted for dropdown selection"""
    sites = parse_pdv_csv()
    return [
        {
            'value': site['sito'],
            'label': f"{site['nome']} ({site['sito']})",
            'ip': site['switch_core_ip'],
            'network': site['network'],
        }
        for site in sites
    ]
