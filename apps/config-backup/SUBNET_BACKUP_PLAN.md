# Piano: Subnet Backup con Discovery Integration

## Obiettivo
Integrare il modulo Huawei Network Discovery nell'app Config Backup per:
1. Scoprire automaticamente gli switch in una subnet prima del backup
2. Evitare la scansione di tutti i 254 IP
3. Gestire credenziali diverse tra Core e L2 switch

---

## Analisi Modulo Discovery Esistente

### Endpoint Discovery
- **URL**: `http://<SERVER_IP>/api/discover`
- **Metodo**: POST
- **Payload**: `{"network": "10.10.4.0/24"}`
- **Community SNMP**: configured in environment

### Formato Risposta Discovery
```json
{
  "success": true,
  "devices": [
    {
      "ip": "10.10.4.25",
      "hostname": "SW-10_L2_Rack0_25",
      "model": "CE6800",
      "uptime": "442 days, 7:42:41.95",
      "snmp": true
    }
  ],
  "total_scanned": 254,
  "message": "Scansione completata: N dispositivi trovati"
}
```

---

## Workflow Proposto

```
┌─────────────────────────────────────────────────────────────────┐
│                    SUBNET BACKUP WORKFLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. UTENTE INSERISCE SUBNET CIDR                                │
│     └── Es: 10.10.4.0/24                                        │
│                                                                  │
│  2. STEP 1: DISCOVERY (automatico)                              │
│     └── POST /api/discover                                      │
│     └── Risposta: lista device con hostname/model               │
│                                                                  │
│  3. STEP 2: CLASSIFICAZIONE DEVICE                              │
│     └── Core Switch: IP termina con .251 (convenzione rete)     │
│     └── L2 Switch: tutti gli altri                              │
│                                                                  │
│  4. STEP 3: SELEZIONE CREDENZIALI                               │
│     ├── Core (.251): usa utente_core / password_core da CSV     │
│     └── L2: usa utente / password standard da CSV               │
│                                                                  │
│  5. STEP 4: BACKUP PARALLELO                                    │
│     └── ThreadPoolExecutor (max 4 worker)                       │
│     └── SSH → Telnet fallback per ogni device                   │
│                                                                  │
│  6. STEP 5: RISULTATI                                           │
│     └── JSON con success/failed per ogni device                 │
│     └── Diff automatico se backup precedente esiste             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Identificazione Core vs L2 Switch

### Metodo 1: Convenzione IP (RACCOMANDATO)
La rete utilizza convenzione: **Core switch = .251**
```python
def is_core_switch(ip):
    return ip.endswith('.251')
```

### Metodo 2: Hostname Pattern (backup)
```python
def is_core_switch_by_hostname(hostname):
    # Pattern comuni per Core
    core_patterns = ['CORE', 'SW-CORE', '_CORE_', 'CE6870']
    return any(p in hostname.upper() for p in core_patterns)
```

### Metodo 3: Model Detection (via SNMP sysDescr)
```python
# Core models (CE6800 series, stackable)
CORE_MODELS = ['CE6870', 'CE6880', 'CE6850', 'CE8800']
# L2 models (access layer)
L2_MODELS = ['S5720', 'S5730', 'S5700', 'S6720', 'CE5800']
```

---

## Gestione Credenziali

### Da Pdv.CSV
```csv
sito;Nome;Network;utente;password;Switch_CORE;utente_Core;password_core
124;PDV_Example;10.10.4.0/24;admin;*****;10.10.4.251;admin_core;*****
```

### Logica Credenziali
```python
def get_credentials(ip, site_data):
    if is_core_switch(ip):
        return {
            'username': site_data['utente_core'] or site_data['utente'],
            'password': site_data['password_core'] or site_data['password']
        }
    else:
        return {
            'username': site_data['utente'],
            'password': site_data['password']
        }
```

---

## Nuovo Endpoint API

### POST /api/backup/discover-and-backup

**Request:**
```json
{
  "subnet": "10.10.4.0/24",
  "sito": "124",                    // Opzionale - per lookup credenziali da CSV
  "username": "admin",              // Se sito non specificato
  "password": "*****",
  "username_core": "admin_core",    // Credenziali separate per core
  "password_core": "*****",
  "backup_core_only": false,        // Solo core switch
  "backup_l2_only": false           // Solo L2 switch
}
```

**Response:**
```json
{
  "success": true,
  "discovery": {
    "total_scanned": 254,
    "devices_found": 5
  },
  "backup": {
    "total": 5,
    "successful": 4,
    "failed": 1,
    "results": [
      {
        "ip": "10.10.4.251",
        "type": "core",
        "success": true,
        "backup_id": 42,
        "has_changes": true
      },
      {
        "ip": "10.10.4.25",
        "type": "l2",
        "success": true,
        "backup_id": 43,
        "has_changes": false
      }
    ],
    "failed": [
      {
        "ip": "10.10.4.30",
        "type": "l2",
        "error": "SSH timeout"
      }
    ]
  }
}
```

---

## Modifiche UI

### Nuova Sezione "Backup Subnet"

```html
<!-- Tab Backup Subnet -->
<div class="backup-section">
  <h3>Backup Subnet con Discovery</h3>

  <!-- Input Subnet -->
  <div class="form-group">
    <label>Subnet CIDR</label>
    <input type="text" id="subnet" placeholder="10.10.4.0/24">
  </div>

  <!-- Selezione Sito (per credenziali auto) -->
  <div class="form-group">
    <label>Sito (opzionale - auto-fill credenziali)</label>
    <select id="site-select">
      <option value="">-- Credenziali manuali --</option>
      <!-- Popolato da API -->
    </select>
  </div>

  <!-- Credenziali Manuali (visibili se no sito) -->
  <div id="manual-credentials">
    <div class="credentials-group">
      <h4>Credenziali L2 Switch</h4>
      <input type="text" id="username" placeholder="Username">
      <input type="password" id="password" placeholder="Password">
    </div>
    <div class="credentials-group">
      <h4>Credenziali Core Switch (.251)</h4>
      <input type="text" id="username-core" placeholder="Username Core">
      <input type="password" id="password-core" placeholder="Password Core">
    </div>
  </div>

  <!-- Opzioni -->
  <div class="options">
    <label><input type="checkbox" id="core-only"> Solo Core Switch</label>
    <label><input type="checkbox" id="l2-only"> Solo L2 Switch</label>
  </div>

  <!-- Pulsante -->
  <button id="btn-subnet-backup" class="btn-primary">
    <i class="fas fa-search"></i> Discovery + Backup
  </button>
</div>
```

### Progress Display

```html
<!-- Progress durante operazione -->
<div id="subnet-progress" class="hidden">
  <div class="progress-step active" id="step-discovery">
    <i class="fas fa-spinner fa-spin"></i> Discovery in corso...
  </div>
  <div class="progress-step" id="step-backup">
    <i class="fas fa-clock"></i> Backup dispositivi...
  </div>
  <div class="progress-bar">
    <div class="progress-fill" style="width: 0%"></div>
    <span class="progress-text">0/0</span>
  </div>
</div>

<!-- Risultati Discovery -->
<div id="discovery-results" class="hidden">
  <h4>Dispositivi Trovati</h4>
  <table>
    <thead>
      <tr>
        <th>IP</th>
        <th>Hostname</th>
        <th>Tipo</th>
        <th>Stato Backup</th>
      </tr>
    </thead>
    <tbody id="devices-table">
      <!-- Popolato dinamicamente -->
    </tbody>
  </table>
</div>
```

---

## Implementazione Backend

### File: routes.py

```python
@bp.route('/api/backup/discover-and-backup', methods=['POST'])
def discover_and_backup():
    """
    Discover devices in subnet then backup configurations.

    1. Call discovery API to find devices
    2. Classify devices (Core vs L2)
    3. Apply correct credentials
    4. Execute parallel backups
    """
    data = request.get_json() or {}

    subnet = data.get('subnet')
    sito = data.get('sito')

    # Validate subnet
    if not subnet:
        return jsonify({'success': False, 'error': 'Subnet required'}), 400

    try:
        network = ipaddress.ip_network(subnet, strict=False)
    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid subnet: {e}'}), 400

    # Get credentials
    if sito:
        site = get_site_by_id(sito)
        if not site:
            return jsonify({'success': False, 'error': f'Site not found: {sito}'}), 404

        creds_l2 = {'username': site['utente'], 'password': site['password']}
        creds_core = {
            'username': site['utente_core'] or site['utente'],
            'password': site['password_core'] or site['password']
        }
        nome_sito = site['nome']
    else:
        creds_l2 = {'username': data.get('username'), 'password': data.get('password')}
        creds_core = {
            'username': data.get('username_core') or data.get('username'),
            'password': data.get('password_core') or data.get('password')
        }
        nome_sito = ''

    # Step 1: Discovery
    discovery_result = call_discovery_api(subnet)
    if not discovery_result.get('success'):
        return jsonify({
            'success': False,
            'error': 'Discovery failed',
            'details': discovery_result
        }), 500

    devices = discovery_result.get('devices', [])
    if not devices:
        return jsonify({
            'success': True,
            'message': 'No devices found in subnet',
            'discovery': {'total_scanned': discovery_result.get('total_scanned', 0), 'devices_found': 0}
        })

    # Step 2: Filter and classify
    backup_core_only = data.get('backup_core_only', False)
    backup_l2_only = data.get('backup_l2_only', False)

    devices_to_backup = []
    for device in devices:
        ip = device['ip']
        is_core = ip.endswith('.251')

        if backup_core_only and not is_core:
            continue
        if backup_l2_only and is_core:
            continue

        devices_to_backup.append({
            **device,
            'type': 'core' if is_core else 'l2',
            'credentials': creds_core if is_core else creds_l2
        })

    # Step 3: Parallel backup
    results = []
    failed = []

    def backup_device(device):
        try:
            with SSHManager(
                device['ip'],
                device['credentials']['username'],
                device['credentials']['password']
            ) as ssh:
                config = ssh.get_current_configuration()
                connection_method = ssh.connection_method

            result = save_backup(
                sito=sito or device['ip'],
                nome_sito=nome_sito,
                ip=device['ip'],
                config=config,
                connection_method=connection_method
            )

            return {
                'success': True,
                'ip': device['ip'],
                'hostname': device.get('hostname', ''),
                'type': device['type'],
                **result
            }
        except Exception as e:
            return {
                'success': False,
                'ip': device['ip'],
                'hostname': device.get('hostname', ''),
                'type': device['type'],
                'error': str(e)
            }

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(backup_device, d): d for d in devices_to_backup}

        for future in as_completed(futures):
            result = future.result()
            if result['success']:
                results.append(result)
            else:
                failed.append(result)

    return jsonify({
        'success': True,
        'discovery': {
            'total_scanned': discovery_result.get('total_scanned', 0),
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
    """Call the existing discovery API"""
    import requests

    try:
        response = requests.post(
            'http://localhost/api/discover',  # Internal call
            json={'network': subnet},
            timeout=120  # Discovery può richiedere tempo
        )
        return response.json()
    except Exception as e:
        logger.error(f"Discovery API call failed: {e}")
        return {'success': False, 'error': str(e)}
```

---

## File da Modificare

| File | Modifiche |
|------|-----------|
| `routes.py` | Aggiungere endpoint `/api/backup/discover-and-backup` |
| `templates/index.html` | Aggiungere sezione Subnet Backup con form |
| `static/js/app.js` | Logica chiamata discovery + backup |
| `static/css/style.css` | Stili per progress e risultati |

---

## Ordine Implementazione

1. **routes.py**: Nuovo endpoint con integrazione discovery
2. **templates/index.html**: Tab/sezione per subnet backup
3. **static/js/app.js**: Logica frontend
4. **Test**: Verifica workflow completo

---

## Considerazioni di Sicurezza

1. **Credenziali**: Mai loggare password in chiaro
2. **CORS**: Discovery API già configurato per localhost
3. **Timeout**: Discovery può richiedere 60-120 secondi per subnet /24
4. **Rate Limiting**: Max 4 backup paralleli per non sovraccaricare switch

---

## Test Cases

1. Subnet con 0 device → messaggio "No devices found"
2. Subnet con solo Core → backup solo .251
3. Credenziali diverse Core/L2 → verifica connessioni separate
4. Discovery timeout → error handling
5. Backup fallito per 1 device → risultato parziale con dettaglio errore
