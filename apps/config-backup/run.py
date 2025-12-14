#!/usr/bin/env python3
"""
Run Config Backup application
Usage: python run.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_backup.app import app

if __name__ == '__main__':
    print("=" * 50)
    print("  Config Backup - Switch Configuration Backup")
    print("=" * 50)
    print(f"  Starting server on http://0.0.0.0:5003")
    print("  Press Ctrl+C to stop")
    print("=" * 50)

    app.run(
        host='0.0.0.0',
        port=5003,
        debug=True
    )
