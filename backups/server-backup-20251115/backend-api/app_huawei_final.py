#!/usr/bin/env python3
"""
ConfigSwitch Backend - Versione Huawei Ottimizzata
Sistema per configurazione automatica switch via SSH
"""

from flask import send_from_directory, Flask, request, jsonify
from flask_cors import CORS
from flask_caching import Cache
import paramiko
import paramiko.transport
import threading
import json
import time
import uuid
from datetime import datetime
import logging
import re
import socket
import subprocess
import platform
from datetime import datetime, timedelta
import telnetlib

app = Flask(__name__)

# Monitoring database configuration
DB_PATH = '/var/www/html/monitoring.db'

CORS(app)

def clean_snmp_value(value):
    """
    Pulisce i valori SNMP grezzi rimuovendo prefissi come STRING:, Timeticks:, INTEGER:
    Examples:
        'STRING: "10_L2_Rack0_25"' -> '10_L2_Rack0_25'
        'Timeticks: (3821656195) 442 days, 7:42:41.95' -> '442 days, 7:42:41.95'
    """
    if not value or not isinstance(value, str):
        return value
    
    value = value.strip()
    
    # Caso 1: STRING: "valore" -> valore
    if value.startswith('STRING:'):
        value = value.replace('STRING:', '', 1).strip()
        value = value.strip('"')
    
    # Caso 2: Timeticks: (numero) testo -> testo
    elif 'Timeticks:' in value:
        if ')' in value:
            value = value.split(')', 1)[1].strip()
    
    # Caso 3: INTEGER: numero -> numero
    elif value.startswith('INTEGER:'):
        value = value.replace('INTEGER:', '', 1).strip()
    
    # Caso 4: Hex-STRING: -> rimuovi
    elif value.startswith('Hex-STRING:'):
        value = value.replace('Hex-STRING:', '', 1).strip()
    
    return value.strip()


# Cache configuration for VLAN data
cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
})

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Storage per processi attivi
active_processes = {}

class ConfigProcess:
    def __init__(self, process_id):
        self.process_id = process_id
        self.status = 'running'
        self.progress = 0
        self.total_hosts = 0
        self.completed_hosts = 0
        self.failed_hosts = 0
        self.logs = []
        self.start_time = datetime.now()
        self.stop_requested = False
        self.switch_results = []  # Track individual switch progress
        
    def add_log(self, message, level='info'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message
        }
        self.logs.append(log_entry)
        if len(self.logs) > 5000:
            self.logs = self.logs[-5000:]
        logger.info(f"[{self.process_id}] {message}")

        
    def init_switch(self, switch_ip, switch_name):
        """Inizializza tracking per singolo switch"""
        self.switch_results.append({
            'switch_ip': switch_ip,
            'switch_name': switch_name,
            'status': 'pending',
            'start_time': None,
            'end_time': None,
            'execution_time': None,
            'error_message': None
        })
        
    def update_switch_status(self, switch_ip, status, error_msg=None):
        """Aggiorna status di singolo switch e calcola tempi"""
        for sw in self.switch_results:
            if sw['switch_ip'] == switch_ip:
                sw['status'] = status
                if status == 'running':
                    sw['start_time'] = datetime.now()
                elif status in ['success', 'failed']:
                    sw['end_time'] = datetime.now()
                    if sw['start_time']:
                        sw['execution_time'] = (sw['end_time'] - sw['start_time']).total_seconds()
                    if error_msg:
                        sw['error_message'] = error_msg
                break
def execute_single_command(hostname, username, password, command, process):
    """Esegue un singolo comando SSH su switch Huawei - VERSIONE ORIGINALE"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Prova PRIMA con credenziali standard, poi fallback a interattivo
        try:
            client.connect(
                hostname=hostname,
                username=username,
                password=password,
                port=22,
                timeout=30,
                look_for_keys=False,
                allow_agent=False
            )
        except paramiko.AuthenticationException:
            # Se fallisce, prova senza credenziali per login interattivo
            try:
                client.connect(
                    hostname=hostname,
                    port=22,
                    timeout=30,
                    look_for_keys=False,
                    allow_agent=False
                )
            except:
                pass  # Continua con shell interattiva

        # Shell interattiva
        shell = client.invoke_shell()
        time.sleep(2)
        
        # Gestisci login Huawei
        login_output = ""
        for _ in range(10):
            if shell.recv_ready():
                chunk = shell.recv(4096).decode('utf-8', errors='ignore')
                login_output += chunk
                
                if 'Username:' in login_output or 'username:' in login_output:
                    shell.send(username + '\n')
                    time.sleep(1)
                    continue
                    
                if 'Password:' in login_output or 'password:' in login_output:
                    shell.send(password + '\n')
                    time.sleep(2)
                    break
                    
                if any(prompt in login_output for prompt in ['>', '#', ']']):
                    break
                    
            time.sleep(0.5)
        
        # Pulisci buffer post-login
        time.sleep(1)
        while shell.recv_ready():
            shell.recv(4096)
        
        # Esegui comando
        shell.send(command + '\n')
        time.sleep(3)
        
        # Leggi output
        output = ""
        for _ in range(20):
            if shell.recv_ready():
                chunk = shell.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
            else:
                time.sleep(0.2)
                if not shell.recv_ready():
                    break
        
        # Pulizia output
        if output:
            clean_output = output.replace(command, '').strip()
            clean_output = re.sub(r'\x1b\[[0-9;]*m', '', clean_output)
            clean_output = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', clean_output)
            lines = [line.strip() for line in clean_output.split('\n') if line.strip()]
            clean_output = '\n'.join(lines)
            
            if clean_output:
                process.add_log(f"Output: {clean_output}")
        
        # Chiudi connessione
        try:
            shell.send('quit\n')
            time.sleep(1)
        except:
            pass

        shell.close()
        client.close()
        return True

    except Exception as e:
        process.add_log(f"Errore comando '{command}': {str(e)}", 'error')
        return False


def telnet_connect(hostname, username, password, commands, process):
    """Esegue tutti i comandi tramite Telnet"""
    try:
        process.add_log(f"Connessione Telnet a {hostname}:23...")
        
        # Connessione Telnet
        tn = telnetlib.Telnet(hostname, port=23, timeout=30)
        
        # Gestisci login interattivo Huawei
        process.add_log("Attendere prompt Username...")
        login_output = tn.read_until(b"Username:", timeout=10).decode('utf-8', errors='ignore')
        
        # Invia username
        tn.write(username.encode('ascii') + b"\n")
        time.sleep(1)
        
        # Attendere Password
        login_output += tn.read_until(b"Password:", timeout=10).decode('utf-8', errors='ignore')
        
        # Invia password
        tn.write(password.encode('ascii') + b"\n")
        time.sleep(2)
        
        # Attendi prompt
        prompt_output = tn.read_until(b">", timeout=10).decode('utf-8', errors='ignore')
        
        process.add_log(f"Connesso via Telnet a {hostname}", 'success')
        
        # Esegui TUTTI i comandi nella STESSA sessione
        success_count = 0
        for i, cmd in enumerate(commands):
            if process.stop_requested:
                break
                
            process.add_log(f"Esecuzione: {cmd}")
            
            # Invia comando
            tn.write(cmd.encode('ascii') + b"\n")
            time.sleep(1)
            
            # Leggi output fino al prompt
            try:
                output = ""
                max_wait = 20
                waited = 0
                
                while waited < max_wait:
                    try:
                        # Prova a leggere con timeout breve
                        chunk = tn.read_very_eager().decode('utf-8', errors='ignore')
                        if chunk:
                            output += chunk
                            
                            # Controlla se abbiamo un prompt
                            if any(p in output for p in ['<', '>', '[', ']', '#']):
                                time.sleep(0.5)
                                # Leggi eventuale output residuo
                                final_chunk = tn.read_very_eager().decode('utf-8', errors='ignore')
                                output += final_chunk
                                break
                        else:
                            time.sleep(0.2)
                            waited += 0.2
                    except EOFError:
                        break
                
                # Pulizia output
                if output:
                    clean_output = output.replace(cmd, '').strip()
                    clean_output = re.sub(r'\x1b\[[0-9;]*m', '', clean_output)  # Rimuovi ANSI
                    clean_output = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', clean_output)  # Rimuovi control chars
                    lines_out = [line.strip() for line in clean_output.split('\n') if line.strip()]
                    clean_output = '\n'.join(lines_out)
                    
                    if clean_output:
                        process.add_log(f"Output: {clean_output}")
                        
                        # Controlla errori
                        if 'Error:' not in clean_output and 'Invalid' not in clean_output:
                            success_count += 1
                else:
                    success_count += 1  # Nessun output = comando eseguito
                    
            except Exception as cmd_error:
                process.add_log(f"Errore comando '{cmd}': {str(cmd_error)}", 'error')
            
            # Aggiorna progresso
            progress = int((i + 1) / len(commands) * 100)
            process.progress = progress
        
        # Chiudi sessione pulitamente
        try:
            tn.write(b"quit\n")
            time.sleep(1)
            tn.write(b"quit\n")  # Due volte per uscire anche da system-view
            time.sleep(1)
        except:
            pass
            
        tn.close()
        
        return success_count > 0
        
    except Exception as e:
        process.add_log(f"Errore Telnet su {hostname}: {str(e)}", 'error')
        return False


def ssh_connect(hostname, username, password, commands, process):
    """Wrapper con fallback SSH → Telnet"""
    
    # Tentativo 1: SSH
    process.add_log(f"Tentativo SSH su {hostname}:22...")
    try:
        result = ssh_connect_internal(hostname, username, password, commands, process)
        if result:
            return True
    except Exception as ssh_error:
        # Verifica se è un errore di CONNESSIONE (non autenticazione)
        error_str = str(ssh_error).lower()
        is_connection_error = any(err in error_str for err in [
            'connection refused', 'timed out', 'no route to host', 
            'network unreachable', 'connection reset', 'channel', 'negotiation', 'unable to connect'
        ])
        
        if is_connection_error:
            process.add_log(f"SSH non disponibile su {hostname}, fallback Telnet...", 'warning')
            
            # Tentativo 2: Telnet
            try:
                return telnet_connect(hostname, username, password, commands, process)
            except Exception as telnet_error:
                process.add_log(f"Anche Telnet fallito: {str(telnet_error)}", 'error')
                return False
        else:
            # Errore SSH non di connessione (es. autenticazione)
            process.add_log(f"Errore SSH (non di connessione): {str(ssh_error)}", 'error')
            return False
    
    return False

def ssh_connect_internal(hostname, username, password, commands, process):
    """Esegue tutti i comandi nella STESSA sessione SSH"""
    try:
        process.add_log(f"Connessione SSH a {hostname}...")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Prova connessione con credenziali
        try:
            client.connect(
                hostname=hostname,
                username=username,
                password=password,
                port=22,
                timeout=30,
                look_for_keys=False,
                allow_agent=False
            )
        except paramiko.AuthenticationException:
            # Fallback senza credenziali per login interattivo
            try:
                client.connect(
                    hostname=hostname,
                    port=22,
                    timeout=30,
                    look_for_keys=False,
                    allow_agent=False
                )
            except:
                pass  # Continua con shell interattiva

        shell = client.invoke_shell(width=200, height=100)
        time.sleep(2)

        # Gestisci login interattivo Huawei
        login_output = ""
        for _ in range(10):
            if shell.recv_ready():
                chunk = shell.recv(4096).decode('utf-8', errors='ignore')
                login_output += chunk

                if 'Username:' in login_output or 'username:' in login_output:
                    shell.send(username + '\n')
                    time.sleep(1)
                    continue

                if 'Password:' in login_output or 'password:' in login_output:
                    shell.send(password + '\n')
                    time.sleep(2)
                    break

                if any(prompt in login_output for prompt in ['>', '#', ']']):
                    break

            time.sleep(0.5)

        process.add_log(f"Connesso a {hostname}", 'success')

        # Pulisci buffer
        time.sleep(1)
        while shell.recv_ready():
            shell.recv(4096)

        # Esegui TUTTI i comandi nella STESSA sessione
        success_count = 0
        for i, cmd in enumerate(commands):
            if process.stop_requested:
                break

            process.add_log(f"Esecuzione: {cmd}")

            # Invia comando
            shell.send(cmd + '\n')
            time.sleep(1)

            # Aspetta output con timeout intelligente
            output = ""
            max_wait = 20  # secondi
            waited = 0

            while waited < max_wait:
                if shell.recv_ready():
                    chunk = shell.recv(4096).decode('utf-8', errors='ignore')
                    output += chunk

                    # Controlla se abbiamo un prompt (comando completato)
                    if any(p in output for p in ['<', '>', '[', ']', '#']):
                        # Aspetta ancora un po' per tutto l'output
                        time.sleep(0.5)
                        if shell.recv_ready():
                            output += shell.recv(4096).decode('utf-8', errors='ignore')
                        break
                else:
                    time.sleep(0.2)
                    waited += 0.2

            # Pulizia output
            if output:
                clean_output = output.replace(cmd, '').strip()
                clean_output = re.sub(r'\x1b\[[0-9;]*m', '', clean_output)  # Rimuovi ANSI
                clean_output = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', clean_output)  # Rimuovi control chars
                lines = [line.strip() for line in clean_output.split('\n') if line.strip()]
                clean_output = '\n'.join(lines)

                if clean_output:
                    process.add_log(f"Output: {clean_output}")

                    # Controlla errori
                    if 'Error:' not in clean_output and 'Invalid' not in clean_output:
                        success_count += 1
            else:
                success_count += 1  # Nessun output = comando eseguito

            # Aggiorna progresso
            progress = int((i + 1) / len(commands) * 100)
            process.progress = progress

        # Chiudi sessione pulitamente
        try:
            shell.send('quit\n')
            time.sleep(1)
            shell.send('quit\n')  # Due volte per uscire anche da system-view
            time.sleep(1)
        except:
            pass

        shell.close()
        client.close()

        return success_count > 0

    except Exception as e:
        process.add_log(f"Errore SSH su {hostname}: {str(e)}", 'error')
        raise

def configure_single_host(host, username, password, commands, process):
    """Wrapper per configurare un singolo host (thread-safe)"""
    try:
        process.update_switch_status(host, 'running')
        success = ssh_connect(host, username, password, commands, process)
        if success:
            process.update_switch_status(host, 'success')
        else:
            process.update_switch_status(host, 'failed', 'Configurazione fallita')
        return (host, success)
    except Exception as e:
        error_msg = str(e)
        process.add_log(f"Errore su {host}: {error_msg}", 'error')
        process.update_switch_status(host, 'failed', error_msg)
        return (host, False)
def process_hosts(process_id, hosts, username, password, commands):
    try:
        process = active_processes[process_id]
        process.total_hosts = len(hosts)
        process.add_log(f"Inizio processo PARALLELO per {len(hosts)} host")
        
        # ThreadPoolExecutor con 8 workers (ottimizzato per SSH)
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        completed = 0
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Avvia tutte le connessioni SSH in parallelo
            futures = {
                executor.submit(configure_single_host, host, username, password, commands, process): host
                for host in hosts
            }
            
            # Processa i risultati man mano che completano
            for future in as_completed(futures):
                if process.stop_requested:
                    process.add_log("Processo interrotto dall'utente", 'warning')
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                    
                try:
                    host, success = future.result()
                    if success:
                        process.completed_hosts += 1
                    else:
                        process.failed_hosts += 1
                except Exception as e:
                    process.add_log(f"Errore durante elaborazione: {str(e)}", 'error')
                    process.failed_hosts += 1
                
                completed += 1
                process.progress = int(completed / len(hosts) * 100)
        
        process.status = 'completed'
        process.add_log(f"Processo completato. Successi: {process.completed_hosts}, Fallimenti: {process.failed_hosts}", 'success')
        
        # Salva statistiche storiche
        completed_times = [sw['execution_time'] for sw in process.switch_results if sw['execution_time'] is not None]
        avg_time = round(sum(completed_times) / len(completed_times), 2) if completed_times else 0
        
        historical_stats.append({
            'process_id': process_id,
            'timestamp': process.start_time.isoformat(),
            'total_switches': process.total_hosts,
            'successful': process.completed_hosts,
            'failed': process.failed_hosts,
            'avg_time': avg_time
        })
        
    except Exception as e:
        process = active_processes.get(process_id)
        if process:
            process.status = 'error'
            process.add_log(f"Errore nel processo: {str(e)}", 'error')



# Monitoring database initialization

# ============================================================================
# MONITORING FUNCTIONS
# ============================================================================

def check_device_reachability(ip, timeout=2):
    """
    Check if device is reachable via ping
    Returns: (is_reachable: bool, response_time_ms: float or None)
    """
    try:
        # Determina il comando ping in base al sistema operativo
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'

        # Esegui ping
        command = ['ping', param, '1', timeout_param, str(timeout), ip]
        output = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 1
        )

        if output.returncode == 0:
            # Device raggiungibile
            output_str = output.stdout.decode()

            # Estrai tempo di risposta (parsing basic, può variare per OS)
            if 'time=' in output_str:
                time_str = output_str.split('time=')[1].split()[0]
                response_time = float(time_str.replace('ms', ''))
                return True, response_time
            return True, None
        else:
            # Device non raggiungibile
            return False, None

    except subprocess.TimeoutExpired:
        print(f'[WARN] Ping timeout for {ip}')
        return False, None
    except Exception as e:
        print(f'[ERROR] Error pinging {ip}: {e}')
        return False, None


def create_alarm(device_id, device_ip, alarm_type, message, severity='warning'):
    """Create a new alarm for a device"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Verifica se esiste già un allarme attivo dello stesso tipo per questo device
        cursor.execute('''
            SELECT id FROM device_alarms
            WHERE device_id=? AND alarm_type=? AND status='active'
        ''', (device_id, alarm_type))

        existing_alarm = cursor.fetchone()

        if existing_alarm:
            # Allarme già esistente, non creare duplicato
            conn.close()
            return existing_alarm[0]

        # Crea nuovo allarme
        cursor.execute('''
            INSERT INTO device_alarms (device_id, device_ip, alarm_type, alarm_message, severity, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        ''', (device_id, device_ip, alarm_type, message, severity))

        alarm_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f'[ALARM] {severity.upper()} - Device {device_ip}: {message}')
        return alarm_id

    except Exception as e:
        print(f'[ERROR] Error creating alarm: {e}')
        return None


def resolve_alarm(device_id, alarm_type):
    """Resolve active alarms of a specific type for a device"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE device_alarms
            SET status='resolved', resolved_at=CURRENT_TIMESTAMP
            WHERE device_id=? AND alarm_type=? AND status='active'
        ''', (device_id, alarm_type))

        resolved_count = cursor.rowcount
        conn.commit()
        conn.close()

        if resolved_count > 0:
            print(f'[INFO] Resolved {resolved_count} alarms of type "{alarm_type}" for device ID {device_id}')

        return resolved_count

    except Exception as e:
        print(f'[ERROR] Error resolving alarm: {e}')
        return 0


def monitoring_background_worker():
    """Background worker that periodically checks monitored devices"""
    print('[MONITORING] ====== WORKER FUNCTION STARTED ======', flush=True)
    print('[MONITORING] Background worker thread started', flush=True)
    print('[MONITORING] Worker will check devices every 30 seconds', flush=True)

    # Wait 5 seconds for application initialization to complete
    print('[MONITORING] Waiting 5 seconds for application initialization...', flush=True)
    time.sleep(5)
    print('[MONITORING] Initialization wait complete, starting monitoring loop', flush=True)

    CHECK_INTERVAL = 30  # seconds between checks
    DB_TIMEOUT = 30  # increased timeout for better reliability

    print('[MONITORING] Entering main loop...', flush=True)

    while True:
        try:
            print(f'[MONITORING] === Starting device check cycle at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===', flush=True)

            # Phase 1: Read devices and collect status data (read-only phase)
            conn = None
            devices_to_check = []
            try:
                print('[MONITORING] Phase 1: Reading devices from database...', flush=True)
                conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT, isolation_level='DEFERRED')
                print('[MONITORING] Database connected successfully (read phase)', flush=True)

                # Enable WAL mode for better concurrency
                conn.execute('PRAGMA journal_mode=WAL')
                cursor = conn.cursor()

                # Get all devices with monitoring_status='active'
                cursor.execute('''
                    SELECT id, ip, name FROM monitored_devices
                    WHERE monitoring_status='active'
                ''')
                devices_to_check = cursor.fetchall()
                device_count = len(devices_to_check)
                print(f'[MONITORING] Found {device_count} active devices to check', flush=True)

            except Exception as read_error:
                print(f'[ERROR] Failed to read devices: {read_error}', flush=True)
                import traceback
                print(f'[ERROR] Traceback: {traceback.format_exc()}', flush=True)
            finally:
                if conn:
                    conn.close()
                    print('[MONITORING] Database connection closed (read phase)', flush=True)

            if len(devices_to_check) == 0:
                print('[MONITORING] No active devices to monitor', flush=True)
                print(f'[MONITORING] Sleeping for {CHECK_INTERVAL} seconds...', flush=True)
                time.sleep(CHECK_INTERVAL)
                continue

            # Phase 2: Check device reachability (no database operations)
            print(f'[MONITORING] Phase 2: Checking {len(devices_to_check)} devices...', flush=True)

            checked_count = 0
            online_count = 0
            offline_count = 0

            # Collect device statuses and pending alarms
            device_updates = []
            pending_alarms = []
            alarms_to_resolve = []

            for device_id, ip, name in devices_to_check:
                try:
                    checked_count += 1
                    print(f'[MONITORING] [{checked_count}/{len(devices_to_check)}] Checking device {ip} (id={device_id})...', flush=True)

                    # Check device reachability
                    is_reachable, response_time = check_device_reachability(ip, timeout=3)

                    if is_reachable:
                        # Device ONLINE
                        online_count += 1
                        device_updates.append({
                            'device_id': device_id,
                            'status': 'online',
                            'ip': ip
                        })

                        # Mark alarm for resolution
                        alarms_to_resolve.append({
                            'device_id': device_id,
                            'alarm_type': 'unreachable'
                        })

                        print(f'[OK] Device {ip} is ONLINE (response: {response_time}ms)', flush=True)

                    else:
                        # Device OFFLINE/UNREACHABLE
                        offline_count += 1
                        device_updates.append({
                            'device_id': device_id,
                            'status': 'offline',
                            'ip': ip
                        })

                        # Add to pending alarms queue
                        device_name = name if name else ip
                        pending_alarms.append({
                            'device_id': device_id,
                            'device_ip': ip,
                            'alarm_type': 'unreachable',
                            'message': f'Device "{device_name}" is not reachable',
                            'severity': 'critical'
                        })

                        print(f'[WARN] Device {ip} is UNREACHABLE - Will create alarm', flush=True)

                except Exception as device_error:
                    print(f'[ERROR] Failed to check device {ip} (id={device_id}): {device_error}', flush=True)
                    import traceback
                    print(f'[ERROR] Traceback: {traceback.format_exc()}', flush=True)
                    continue

            # Phase 3: Batch write updates and alarms (single short-lived connection)
            print('[MONITORING] Phase 3: Writing updates to database...', flush=True)
            conn = None
            max_retries = 3
            retry_count = 0
            write_success = False

            while retry_count < max_retries and not write_success:
                try:
                    if retry_count > 0:
                        wait_time = 2 ** retry_count  # exponential backoff
                        print(f'[RETRY] Waiting {wait_time}s before retry {retry_count + 1}/{max_retries}...', flush=True)
                        time.sleep(wait_time)

                    print(f'[MONITORING] Opening database for batch write (attempt {retry_count + 1}/{max_retries})...', flush=True)
                    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT, isolation_level=None)  # autocommit off

                    # Enable WAL mode for better concurrency
                    conn.execute('PRAGMA journal_mode=WAL')
                    cursor = conn.cursor()

                    # Start immediate transaction to get write lock upfront
                    cursor.execute('BEGIN IMMEDIATE')
                    print('[MONITORING] Write transaction started (IMMEDIATE mode)', flush=True)

                    # Update device statuses
                    for update in device_updates:
                        cursor.execute('''
                            UPDATE monitored_devices
                            SET device_status=?, last_check=CURRENT_TIMESTAMP
                            WHERE id=?
                        ''', (update['status'], update['device_id']))

                    print(f'[MONITORING] Updated {len(device_updates)} device statuses', flush=True)

                    # Resolve alarms
                    for resolve in alarms_to_resolve:
                        cursor.execute('''
                            UPDATE device_alarms
                            SET status='resolved', resolved_at=CURRENT_TIMESTAMP
                            WHERE device_id=? AND alarm_type=? AND status='active'
                        ''', (resolve['device_id'], resolve['alarm_type']))

                    resolved_count = sum(1 for resolve in alarms_to_resolve)
                    if resolved_count > 0:
                        print(f'[MONITORING] Resolved {resolved_count} alarms', flush=True)

                    # Create new alarms (batch insert with duplicate check)
                    alarms_created = 0
                    for alarm in pending_alarms:
                        # Check if alarm already exists
                        cursor.execute('''
                            SELECT id FROM device_alarms
                            WHERE device_id=? AND alarm_type=? AND status='active'
                        ''', (alarm['device_id'], alarm['alarm_type']))

                        existing = cursor.fetchone()
                        if not existing:
                            cursor.execute('''
                                INSERT INTO device_alarms (device_id, device_ip, alarm_type, alarm_message, severity, status)
                                VALUES (?, ?, ?, ?, ?, 'active')
                            ''', (alarm['device_id'], alarm['device_ip'], alarm['alarm_type'],
                                  alarm['message'], alarm['severity']))
                            alarms_created += 1
                            print(f'[ALARM] Created {alarm["severity"].upper()} alarm for {alarm["device_ip"]}: {alarm["message"]}', flush=True)

                    if alarms_created > 0:
                        print(f'[MONITORING] Created {alarms_created} new alarms', flush=True)

                    # Commit all changes
                    conn.commit()
                    print('[MONITORING] All database changes committed successfully', flush=True)
                    write_success = True

                except sqlite3.OperationalError as db_error:
                    retry_count += 1
                    print(f'[ERROR] Database locked during write (attempt {retry_count}/{max_retries}): {db_error}', flush=True)
                    if conn:
                        try:
                            conn.rollback()
                        except:
                            pass

                    if retry_count >= max_retries:
                        print(f'[ERROR] Failed to write updates after {max_retries} retries', flush=True)
                        import traceback
                        print(f'[ERROR] Traceback: {traceback.format_exc()}', flush=True)

                except Exception as write_error:
                    retry_count += 1
                    print(f'[ERROR] Unexpected error during write: {write_error}', flush=True)
                    if conn:
                        try:
                            conn.rollback()
                        except:
                            pass
                    import traceback
                    print(f'[ERROR] Traceback: {traceback.format_exc()}', flush=True)

                finally:
                    if conn:
                        try:
                            conn.close()
                            print('[MONITORING] Database connection closed (write phase)', flush=True)
                        except Exception as close_error:
                            print(f'[ERROR] Error closing database connection: {close_error}', flush=True)

            print(f'[MONITORING] === Check cycle completed ===', flush=True)
            print(f'[MONITORING] Summary: {checked_count} checked, {online_count} online, {offline_count} offline', flush=True)
            print(f'[MONITORING] Next check in {CHECK_INTERVAL} seconds', flush=True)

            # Sleep before next cycle
            print(f'[MONITORING] Sleeping for {CHECK_INTERVAL} seconds...', flush=True)
            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f'[MONITORING] CRITICAL ERROR in background worker: {e}', flush=True)
            import traceback
            print(f'[ERROR] Full traceback: {traceback.format_exc()}', flush=True)
            print(f'[MONITORING] Worker will retry in 60 seconds after critical error', flush=True)
            time.sleep(60)  # Wait 1 minute before retrying after critical error

def init_monitoring_db():
    """Initialize monitoring database with schema"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitored_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT UNIQUE NOT NULL,
                name TEXT,
                monitoring_status TEXT DEFAULT 'pending',
                device_status TEXT DEFAULT 'unknown',
                last_check TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_monitored_devices_ip ON monitored_devices(ip)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_monitoring_status ON monitored_devices(monitoring_status)')

        conn.commit()
        conn.close()
        logger.info('Monitoring database initialized successfully')
    except Exception as e:
        logger.error(f'Database initialization error: {e}')
        raise

@app.route('/api/execute', methods=['POST'])


def init_alarms_db():
    """Initialize alarms database table"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Tabella allarmi
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                device_ip TEXT NOT NULL,
                alarm_type TEXT NOT NULL,
                alarm_message TEXT,
                severity TEXT DEFAULT 'warning',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES monitored_devices(id)
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alarms_device_id ON device_alarms(device_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alarms_status ON device_alarms(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alarms_severity ON device_alarms(severity)')

        conn.commit()
        conn.close()
        print('[MONITOR] Alarms database initialized')
    except Exception as e:
        print(f'[ERROR] Error initializing alarms database: {e}')

def execute_config():
    try:
        # Debug logging
        logger.info(f"Ricevuta richiesta POST: {request.method}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Data raw: {request.get_data()}")
        
        data = request.json
        logger.info(f"Data parsed: {data}")
        
        # Validazione input
        required_fields = ['hosts', 'username', 'password', 'commands']
        for field in required_fields:
            if field not in data or not data[field]:
                logger.error(f"Campo mancante: {field}")
                return jsonify({'error': f'Campo mancante: {field}'}), 400
        
        # Creazione processo
        process_id = str(uuid.uuid4())
        process = ConfigProcess(process_id)
        active_processes[process_id] = process
        
        # Parsing hosts
        hosts = []
        if isinstance(data['hosts'], str):
            for line in data['hosts'].strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    hosts.append(line)
        else:
            hosts = data['hosts']
        
        # Parsing comandi
        commands = []
        if isinstance(data['commands'], str):
            for line in data['commands'].strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    commands.append(line)
        else:
            commands = data['commands']
        
        
        # Inizializza tracking per ogni switch
        for host in hosts:
            switch_name = f"SW-{host.replace('.', '-')}"
            process.init_switch(host, switch_name)
        # Avvio thread
        thread = threading.Thread(
            target=process_hosts,
            args=(process_id, hosts, data['username'], data['password'], commands),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            'success': True,
            'process_id': process_id,
            'message': f'Processo avviato per {len(hosts)} host'
        })
        
    except Exception as e:
        logger.error(f"Errore in execute_config: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def backend_status():
    """Status generale del backend"""
    return jsonify({
        'success': True,
        'status': 'running',
        'active_processes': len(active_processes),
        'message': 'Backend operativo'
    })

@app.route('/api/status/<process_id>', methods=['GET'])
def get_status(process_id):
    try:
        process = active_processes.get(process_id)
        if not process:
            return jsonify({'error': 'Processo non trovato'}), 404

        # Calcola failed switch names
        failed_switches = [
            sw['switch_name'] 
            for sw in process.switch_results 
            if sw['status'] == 'failed'
        ]
        
        # Calcola tempo medio esecuzione
        completed_times = [
            sw['execution_time'] 
            for sw in process.switch_results 
            if sw['execution_time'] is not None
        ]
        avg_time = round(sum(completed_times) / len(completed_times), 2) if completed_times else 0

        return jsonify({
            'status': process.status,
            'progress': process.progress,
            'total_hosts': process.total_hosts,
            'completed_hosts': process.completed_hosts,
            'failed_hosts': process.failed_hosts,
            'switch_results': process.switch_results,
            'failed_switch_names': failed_switches,
            'avg_execution_time': avg_time,
            'logs': process.logs,
            'start_time': process.start_time.isoformat()
        })

    except Exception as e:
        logger.error(f"Errore in get_status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop/<process_id>', methods=['POST'])
def stop_process(process_id):
    try:
        process = active_processes.get(process_id)
        if not process:
            return jsonify({'error': 'Processo non trovato'}), 404
        
        process.stop_requested = True
        process.add_log("Richiesta di interruzione ricevuta", 'warning')
        
        return jsonify({
            'success': True,
            'message': 'Richiesta di interruzione inviata'
        })
        
    except Exception as e:
        logger.error(f"Errore in stop_process: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/processes', methods=['GET'])
def list_processes():
    try:
        processes = []
        for pid, process in active_processes.items():
            processes.append({
                'process_id': pid,
                'status': process.status,
                'progress': process.progress,
                'total_hosts': process.total_hosts,
                'completed_hosts': process.completed_hosts,
                'failed_hosts': process.failed_hosts,
                'start_time': process.start_time.isoformat()
            })

        return jsonify({'processes': processes})

    except Exception as e:
        logger.error(f"Errore in list_processes: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint per discovery.html"""
    return jsonify({
        'success': True,
        'status': 'running',
        'message': 'Backend Flask attivo su porta 5001',
        'endpoints': {
            'discovery': '/api/discovery',
            'discover': '/api/discover',
            'execute': '/api/execute',
            'status': '/api/status/<process_id>'
        }
    })

@app.route('/api/discovery', methods=['POST', 'GET'])
@app.route('/api/discover', methods=['POST', 'GET'])  # Alias per compatibilità
def network_discovery():
    """
    Network Discovery con SNMP (gsmon community)
    Scansiona rete per dispositivi Huawei
    """
    try:
        if request.method == 'GET':
            # Status check
            return jsonify({
                'success': True,
                'status': 'ready',
                'message': 'Network Discovery API attiva',
                'community': 'gsmon'
            })

        # POST - Avvia scansione
        data = request.json or {}
        network = data.get('network', '10.10.4.0/24')
        community = data.get('community', 'gsmon')
        sync = data.get('sync', True)  # Default sincrono per compatibilità HTML

        logger.info(f"Richiesta discovery per rete: {network}, community: {community}, sync: {sync}")

        # Crea processo discovery
        process_id = str(uuid.uuid4())
        process = ConfigProcess(process_id)
        active_processes[process_id] = process

        process.add_log(f"Avvio scansione rete: {network}")
        process.add_log(f"Community SNMP: {community}")

        if sync:
            # Modalità SINCRONA: esegui e ritorna risultati subito
            perform_snmp_discovery(process_id, network, community)
            devices = getattr(process, 'discovered_devices', [])

            return jsonify({
                'success': True,
                'process_id': process_id,
                'network': network,
                'devices': devices,
                'total_scanned': process.total_hosts,
                'message': f'Scansione completata: {len(devices)} dispositivi trovati'
            })
        else:
            # Modalità ASINCRONA: avvia in background
            thread = threading.Thread(
                target=perform_snmp_discovery,
                args=(process_id, network, community),
                daemon=True
            )
            thread.start()

            return jsonify({
                'success': True,
                'process_id': process_id,
                'network': network,
                'message': f'Scansione avviata per {network}'
            })

    except Exception as e:
        logger.error(f"Errore in network_discovery: {str(e)}")
        return jsonify({'error': str(e)}), 500


def scan_single_host(host_str, community, process):
    """Scansiona un singolo host (ping + SNMP) - OTTIMIZZATO PER PARALLELIZZAZIONE"""
    import subprocess
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '1', host_str],
            capture_output=True,
            timeout=2
        )
        
        if result.returncode == 0:
            try:
                snmp_result = subprocess.run(
                    ['snmpget', '-v2c', '-c', community, host_str,
                     '1.3.6.1.2.1.1.1.0',
                     '1.3.6.1.2.1.1.5.0',
                     '1.3.6.1.2.1.1.3.0'],
                    capture_output=True,
                    timeout=3
                )
                
                if snmp_result.returncode == 0:
                    output = snmp_result.stdout.decode('utf-8', errors='ignore')
                    lines = output.strip().split('\n')
                    
                    description = ''
                    hostname = ''
                    uptime = ''
                    
                    for line in lines:
                        if 'iso.3.6.1.2.1.1.1.0' in line:
                            description = line.split('=')[1].strip() if '=' in line else ''
                        elif 'iso.3.6.1.2.1.1.5.0' in line:
                            hostname = line.split('=')[1].strip() if '=' in line else ''
                        elif 'iso.3.6.1.2.1.1.3.0' in line:
                            uptime = line.split('=')[1].strip() if '=' in line else ''
                    
                    return {
                        'ip': host_str,
                        'hostname': clean_snmp_value(hostname),
                        'model': clean_snmp_value(description),
                        'uptime': clean_snmp_value(uptime),
                        'snmp': True
                    }
            except subprocess.TimeoutExpired:
                pass
    except subprocess.TimeoutExpired:
        pass
    
    return None


def perform_snmp_discovery(process_id, network, community):
    """Esegue la scansione SNMP della rete - VERSIONE PARALLELIZZATA CON ThreadPoolExecutor"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import ipaddress
    
    try:
        process = active_processes[process_id]
        process.add_log("Parsing network range...")
        
        net = ipaddress.ip_network(network, strict=False)
        hosts = list(net.hosts())
        process.total_hosts = len(hosts)
        
        process.add_log(f"Scansione parallela di {len(hosts)} IP con 20 thread...")
        
        discovered = []
        
        max_workers = 20
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_host = {
                executor.submit(scan_single_host, str(host), community, process): host
                for host in hosts
            }
            
            for i, future in enumerate(as_completed(future_to_host)):
                if process.stop_requested:
                    executor.shutdown(wait=False)
                    break
                
                result = future.result()
                if result:
                    discovered.append(result)
                    process.add_log(f"✓ SNMP: {result['ip']} ({result['hostname']})")
                
                process.completed_hosts += 1
                process.progress = int((i + 1) / len(hosts) * 100)
        
        process.discovered_devices = discovered
        process.status = 'completed'
        process.add_log(f"Scansione completata. Dispositivi trovati: {len(discovered)}", 'success')
        
    except Exception as e:
        process = active_processes.get(process_id)
        if process:
            process.status = 'error'
            process.add_log(f"Errore discovery: {str(e)}", 'error')

            process.add_log(f"Errore discovery: {str(e)}", 'error')

@app.route('/api/discovery/results/<process_id>', methods=['GET'])
def get_discovery_results(process_id):
    """Ottieni risultati discovery"""
    try:
        process = active_processes.get(process_id)
        if not process:
            return jsonify({'error': 'Processo non trovato'}), 404

        results = {
            'status': process.status,
            'progress': process.progress,
            'total_hosts': process.total_hosts,
            'completed_hosts': process.completed_hosts,
            'devices': getattr(process, 'discovered_devices', []),
            'logs': process.logs
        }

        return jsonify(results)

    except Exception as e:
        logger.error(f"Errore in get_discovery_results: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/discovery/export/<process_id>', methods=['GET'])
def export_discovery_ips(process_id):
    """Esporta IP scoperti in formato TXT"""
    try:
        process = active_processes.get(process_id)
        if not process:
            return "Process not found", 404

        devices = getattr(process, 'discovered_devices', [])

        # Genera TXT
        txt_content = f"# Network Discovery Results\n"
        txt_content += f"# Total devices: {len(devices)}\n"
        txt_content += f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        for device in devices:
            txt_content += f"{device['ip']}\n"

        return txt_content, 200, {
            'Content-Type': 'text/plain',

            'Content-Disposition': f'attachment; filename=discovery_{process_id[:8]}.txt'
        }

    except Exception as e:
        logger.error(f"Errore in export_discovery_ips: {str(e)}")
        return str(e), 500
#  VLAN Routes Integration
from vlan_routes import register_vlan_routes
import sqlite3
register_vlan_routes(app, cache, active_processes)



@app.route("/")
@app.route("/vlan")
@app.route("/vlan-viewer")
def vlan_viewer():
    """Serve the VLAN visualization HTML interface"""
    return send_from_directory("/home/mmereu", "vlan-viewer.html")



# Storage statistiche storiche (in-memory)
historical_stats = []

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Ritorna statistiche storiche delle esecuzioni"""
    try:
        if not historical_stats:
            return jsonify({
                'total_executions': 0,
                'recent_executions': [],
                'global_avg_time': 0,
                'global_success_rate': 0
            })
        
        # Calcola metriche globali
        total_switches = sum(stat['total_switches'] for stat in historical_stats)
        total_successful = sum(stat['successful'] for stat in historical_stats)
        global_success_rate = round((total_successful / total_switches * 100) if total_switches > 0 else 0, 2)
        
        all_times = []
        for stat in historical_stats:
            if 'avg_time' in stat and stat['avg_time'] > 0:
                all_times.append(stat['avg_time'])
        global_avg_time = round(sum(all_times) / len(all_times), 2) if all_times else 0
        
        return jsonify({
            'total_executions': len(historical_stats),
            'recent_executions': historical_stats[-10:],  # Last 10
            'global_avg_time': global_avg_time,
            'global_success_rate': global_success_rate
        })
    except Exception as e:
        logger.error(f"Errore in get_statistics: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ==================== MONITORING ENDPOINTS ====================

@app.route('/api/monitoring/add', methods=['POST', 'OPTIONS'])
def add_monitoring():
    """Add device to monitoring list"""
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.json
        ip = data.get('ip')
        name = data.get('name', '')

        if not ip:
            return jsonify({'error': 'IP address required'}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO monitored_devices (ip, name, monitoring_status)
            VALUES (?, ?, 'active')
        ''', (ip, name))

        conn.commit()
        device_id = cursor.lastrowid
        conn.close()

        logger.info(f'Device added to monitoring: {ip} ({name})')
        return jsonify({
            'status': 'success',
            'device_id': device_id,
            'ip': ip,
            'name': name
        })

    except Exception as e:
        logger.error(f'Error adding device: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/monitoring/status/<ip>', methods=['GET'])
def get_monitoring_status(ip):
    """Get device monitoring status"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, ip, name, device_status, monitoring_status, last_check
            FROM monitored_devices WHERE ip = ?
        ''', (ip,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({'error': 'Device not found'}), 404

        return jsonify({
            'id': row[0],
            'ip': row[1],
            'name': row[2],
            'device_status': row[3],
            'monitoring_status': row[4],
            'last_check': row[5]
        })

    except Exception as e:
        logger.error(f'Error getting status: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/monitoring/list', methods=['GET'])
def list_monitoring():
    """List all monitored devices"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, ip, name, device_status, monitoring_status, last_check, created_at
            FROM monitored_devices ORDER BY created_at DESC
        ''')

        devices = []
        for row in cursor.fetchall():
            devices.append({
                'id': row[0],
                'ip': row[1],
                'name': row[2],
                'device_status': row[3],
                'monitoring_status': row[4],
                'last_check': row[5],
                'created_at': row[6]
            })

        conn.close()

        return jsonify({'devices': devices})

    except Exception as e:
        logger.error(f'Error listing devices: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/monitoring/remove/<device_id>', methods=['DELETE'])
def remove_monitoring(device_id):
    """Remove device from monitoring"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM monitored_devices WHERE id = ?', (device_id,))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Device not found'}), 404

        conn.close()
        logger.info(f'Device removed from monitoring: ID {device_id}')
        return jsonify({'status': 'success'})

    except Exception as e:
        logger.error(f'Error removing device: {e}')
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ALARM API ENDPOINTS
# ============================================================================

@app.route('/api/alarms/list', methods=['GET'])
def list_alarms():
    """List all alarms with optional filters"""
    try:
        status_filter = request.args.get('status', 'active')  # active, resolved, all
        severity_filter = request.args.get('severity')  # critical, warning, info

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        query = '''
            SELECT
                a.id, a.device_id, a.device_ip, a.alarm_type,
                a.alarm_message, a.severity, a.status,
                a.created_at, a.resolved_at,
                d.name as device_name
            FROM device_alarms a
            LEFT JOIN monitored_devices d ON a.device_id = d.id
        '''

        conditions = []
        params = []

        if status_filter != 'all':
            conditions.append('a.status = ?')
            params.append(status_filter)

        if severity_filter:
            conditions.append('a.severity = ?')
            params.append(severity_filter)

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += ' ORDER BY a.created_at DESC LIMIT 100'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        alarms = []
        for row in rows:
            alarms.append({
                'id': row[0],
                'device_id': row[1],
                'device_ip': row[2],
                'alarm_type': row[3],
                'alarm_message': row[4],
                'severity': row[5],
                'status': row[6],
                'created_at': row[7],
                'resolved_at': row[8],
                'device_name': row[9]
            })

        return jsonify({
            'success': True,
            'alarms': alarms,
            'count': len(alarms)
        })

    except Exception as e:
        print(f'[ERROR] Error listing alarms: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/alarms/count', methods=['GET'])
def count_active_alarms():
    """Count active alarms"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT severity, COUNT(*)
            FROM device_alarms
            WHERE status='active'
            GROUP BY severity
        ''')

        rows = cursor.fetchall()
        conn.close()

        counts = {'critical': 0, 'warning': 0, 'info': 0, 'total': 0}

        for severity, count in rows:
            counts[severity] = count
            counts['total'] += count

        return jsonify({
            'success': True,
            'counts': counts
        })

    except Exception as e:
        print(f'[ERROR] Error counting alarms: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/alarms/resolve/<int:alarm_id>', methods=['POST'])
def resolve_alarm_endpoint(alarm_id):
    """Manually resolve an alarm"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE device_alarms
            SET status='resolved', resolved_at=CURRENT_TIMESTAMP
            WHERE id=? AND status='active'
        ''', (alarm_id,))

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Alarm not found or already resolved'}), 404

        conn.commit()
        conn.close()

        print(f'[INFO] Alarm {alarm_id} manually resolved')
        return jsonify({'success': True, 'message': 'Alarm resolved'})

    except Exception as e:
        print(f'[ERROR] Error resolving alarm: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_monitoring_db()
    # Inizializza database allarmi
    init_alarms_db()

    # Avvia background monitoring thread
    monitoring_thread = threading.Thread(
        target=monitoring_background_worker,
        daemon=True,
        name='MonitoringWorker'
    )
    monitoring_thread.start()
    print('[MONITORING] Background thread started')

    print("🚀 ConfigSwitch Backend avviato")
    print("📊 Dashboard: http://172.24.1.33:8081")
    print("🔧 API endpoint: http://172.24.1.33:8081/api/")
    app.run(host='0.0.0.0', port=5001, debug=False)