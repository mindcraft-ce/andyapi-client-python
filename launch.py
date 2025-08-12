#!/usr/bin/env python3
import sys
import os
import subprocess
import json

CONFIG_DIR = 'local_client'
CONFIG = os.path.join(CONFIG_DIR, 'client_config.json')

def load_config(config_path):
    with open(config_path, 'r') as config_file:
        return json.load(config_file)

def main():
    config = load_config(CONFIG)
    print("🌐 Starting Andy API Local Client Web Interface...")
    print(f"   Web interface will be available at: http://localhost:{config['flask_port']}")
    print(f"   Andy API server: {config['andy_api_url']}")
    print(f"   Base API server: {config['base_api_url']}")
    print()

    subprocess.run([sys.executable, "app.py"])

if __name__ == "__main__":
    main()
