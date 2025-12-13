#!/usr/bin/env python3
"""
Huawei Switch Migration Tool - Main Entry Point
Run on: http://YOUR_SERVER:9999
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Run on port 9999, accessible from network
    app.run(host='0.0.0.0', port=9999, debug=False)
