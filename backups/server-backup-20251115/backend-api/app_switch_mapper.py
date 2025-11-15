#!/usr/bin/env python3
"""
Switch Port Mapper Application - FIXED VERSION
Adds robust error handling to prevent empty ports array bug
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from snmp_client import SNMPClient
from snmp_client_enhanced import get_port_status, detect_stack, get_port_count
from snmp_optimized import OptimizedSNMPClient

app = Flask(__name__, static_folder="frontend/dist")
CORS(app, origins=["*"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/api/switch/map", methods=["POST"])
def get_switch_map():
    """
    Get complete switch port mapping with VLANs, status, and visual layout
    """
    try:
        data = request.get_json()
        switch_ip = data.get("switch_ip")
        community = data.get("community", "gsmon")

        if not switch_ip:
            return jsonify({"success": False, "error": "switch_ip required"}), 400

        logger.info(f"Querying switch {switch_ip} for port mapping")

        start_time = time.time()
        client = SNMPClient(switch_ip, community)
        opt_client = OptimizedSNMPClient(client)

        # Execute ALL SNMP queries in parallel for maximum performance
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_switch_data = executor.submit(opt_client.get_switch_data_optimized)
            future_port_status = executor.submit(get_port_status, client)
            future_stack_info = executor.submit(detect_stack, client)
            future_port_count = executor.submit(get_port_count, client)

            # Collect results with timeout and error handling
            try:
                switch_data = future_switch_data.result(timeout=30)
            except Exception as e:
                logger.error(f"Failed to get switch data: {e}")
                raise ValueError(f"SNMP query failed: {e}")

            port_status_map = future_port_status.result()
            stack_info = future_stack_info.result()
            port_count_info = future_port_count.result()

        # CRITICAL FIX: Validate switch_data structure before using it
        if not switch_data or not isinstance(switch_data, dict):
            logger.error(f"Invalid switch_data type: {type(switch_data)}")
            raise ValueError("Invalid SNMP response structure")

        if "ports" not in switch_data:
            logger.error(f"Missing 'ports' key. Available keys: {list(switch_data.keys())}")
            raise ValueError("SNMP response missing port data")

        # Log warning if ports dict is empty (helps debugging)
        if not switch_data["ports"]:
            logger.warning(f"Empty ports dict returned! VLANs present: {len(switch_data.get('vlans', {}))}")

        port_mapping = client.get_port_mapping()

        query_time = time.time() - start_time
        logger.info(f"ALL SNMP queries completed in {query_time:.2f} seconds (PARALLEL)")
        logger.info(f"Retrieved {len(switch_data['ports'])} ports from switch_data")

        ports_output = []

        # Iterate with per-port error handling
        for bridge_port_str, port_info in switch_data["ports"].items():
            try:
                bridge_port = int(bridge_port_str)
                ifindex = port_mapping.get(bridge_port, bridge_port)

                status_info = port_status_map.get(ifindex, {"is_up": False, "oper_status": "unknown"})

                # Determine if trunk
                is_trunk = (
                    "trunk" in port_info["interface_name"].lower() or
                    (port_info["pvid"] in [1, 999, 4094] and "Gig" in port_info["interface_name"])
                )

                port_output = {
                    "port_number": bridge_port,
                    "interface_name": port_info["interface_name"],
                    "status": "up" if status_info["is_up"] else "down",
                    "mode": "trunk" if is_trunk else "access",
                    "vlan_id": port_info["pvid"],
                    "allowed_vlans": port_info.get("allowed_vlans", []),
                    "is_trunk": is_trunk
                }

                ports_output.append(port_output)
            except Exception as e:
                logger.warning(f"Skipping port {bridge_port_str} due to error: {e}")
                continue

        ports_output.sort(key=lambda p: p["port_number"])

        # Build VLAN summary
        vlans_on_ports = {}

        for vlan_id_str, vlan_info in switch_data.get("vlans", {}).items():
            vlans_on_ports[vlan_id_str] = {
                "name": vlan_info["name"],
                "ports": []
            }

        for port in ports_output:
            vlan_id = str(port["vlan_id"])
            if vlan_id in vlans_on_ports:
                vlans_on_ports[vlan_id]["ports"].append(port["port_number"])

        vlans_final = {}
        for vid, vinfo in vlans_on_ports.items():
            if vinfo["ports"]:
                if vid == "1" and len(vinfo["ports"]) <= 2:
                    continue
                vlans_final[vid] = vinfo

        response = {
            "success": True,
            "switch_info": {
                "hostname": switch_data.get("hostname", "Unknown"),
                "model": switch_data.get("model", "Unknown"),
                "ip": switch_ip,
                "total_ports": port_count_info["total_ports"],
                "is_stack": stack_info["is_stack"],
                "stack_members": stack_info["stack_members"]
            },
            "ports": ports_output,
            "vlans": vlans_final
        }

        logger.info(f"Successfully mapped {len(ports_output)} ports from {switch_ip}")

        # VALIDATION: Log error if returning empty ports
        if not ports_output:
            logger.error(f"CRITICAL: Returning empty ports array! switch_data had {len(switch_data.get('ports', {}))} ports")

        return jsonify(response)

    except TimeoutError as e:
        logger.error(f"SNMP timeout: {e}")
        return jsonify({"success": False, "error": "SNMP timeout - switch unreachable"}), 504

    except Exception as e:
        logger.error(f"Error mapping switch: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/discover", methods=["POST"])
def discover_network():
    """
    Discover Huawei switches on a network using SNMP community 'gsmon'
    Expects: {"network": "10.10.4.0/24"} or {"network": "10.10.4.25"}
    Returns: {"devices": [...], "scan_time": "..."}
    """
    import ipaddress
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    try:
        data = request.get_json()
        network = data.get("network")
        
        if not network:
            return jsonify({"error": "network parameter required"}), 400
        
        logger.info(f"Starting network discovery for {network}")
        start_time = time.time()
        
        # Parse network (CIDR or single IP)
        try:
            if "/" in network:
                ip_network = ipaddress.ip_network(network, strict=False)
                ip_list = [str(ip) for ip in ip_network.hosts()]
            else:
                ip_list = [network]
        except ValueError as e:
            return jsonify({"error": f"Invalid network format: {e}"}), 400
        
        logger.info(f"Scanning {len(ip_list)} IP addresses")
        
        discovered_devices = []
        community = "gsmon"  # Fixed community as per requirements
        
        def check_device(ip):
            """Check if IP is a Huawei switch with SNMP community gsmon"""
            try:
                client = SNMPClient(ip, community, timeout=2, retries=1)
                
                # Get system info (quick check)
                hostname = client.get_hostname()
                model = client.get_model()
                uptime = client.get_uptime()
                
                if hostname and model:  # Valid Huawei switch
                    return {
                        "ip": ip,
                        "name": hostname,
                        "model": model,
                        "uptime": uptime
                    }
            except Exception as e:
                logger.debug(f"IP {ip} not reachable: {e}")
                return None
            return None
        
        # Parallel scanning for speed
        max_workers = min(50, len(ip_list))  # Max 50 concurrent SNMP checks
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {executor.submit(check_device, ip): ip for ip in ip_list}
            
            for future in as_completed(future_to_ip):
                result = future.result()
                if result:
                    discovered_devices.append(result)
                    logger.info(f"Found device: {result['ip']} - {result['name']}")
        
        scan_time = f"{time.time() - start_time:.2f}s"
        logger.info(f"Discovery complete: {len(discovered_devices)} devices found in {scan_time}")
        
        return jsonify({
            "devices": discovered_devices,
            "scan_time": scan_time,
            "total_scanned": len(ip_list),
            "total_found": len(discovered_devices)
        })
        
    except Exception as e:
        logger.error(f"Discovery error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Huawei Network Discovery API",
        "timestamp": time.time()
    })

@app.route("/<path:path>")
def serve_static(path):
    """Serve static files"""
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        mapper_path = os.path.join(app.static_folder, "switch-mapper.html")
        if os.path.exists(mapper_path):
            return send_from_directory(app.static_folder, "switch-mapper.html")
        else:
            return "Switch Mapper Frontend Not Found", 404

@app.route("/")
def index():
    """Serve index"""
    return serve_static("switch-mapper.html")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5002)
    args = parser.parse_args()

    logger.info(f"Starting Switch Mapper on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)
