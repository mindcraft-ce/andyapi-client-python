#!/usr/bin/env python3
"""
Andy API Local Client - OpenAI-Compatible Version
A web-based interface for hosting models from any OpenAI-compatible endpoint
and connecting to the Andy API compute pool.
"""

import os
import json
import time
import threading
import requests
import uuid
import sqlite3
import logging
import openai
from datetime import datetime
from flask import Flask, render_template, request, jsonify, url_for, send_from_directory
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from urllib.parse import unquote

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'andy-local-client-secret-key-openai'

# --- Default Configuration Constants ---
DEFAULT_ANDY_API_URL = 'https://andy.mindcraft-ce.com'
DEFAULT_API_BASE = 'http://localhost:11434/v1'

# --- Configuration ---
CONFIG_DIR = 'local_client'
CONFIG_FILE = os.path.join(CONFIG_DIR, 'client_config.json')
MODELS_CONFIG_FILE = os.path.join(CONFIG_DIR, 'models_config.json')
DB_FILE = os.path.join(CONFIG_DIR, 'local_client.db')
UUID_FILE = os.path.join(CONFIG_DIR, 'client_uuid.txt')


@dataclass
class ModelConfig:
    name: str
    enabled: bool = False
    supports_embedding: bool = False
    supports_vision: bool = False
    supports_audio: bool = False
    max_concurrent: int = 2
    context_length: int = 4096
    quantization: str = "unknown"

@dataclass
class ClientStats:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    average_tokens_per_second: float = 0.0
    last_request_time: Optional[datetime] = None
    uptime_start: datetime = datetime.now()

class LocalClient:
    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.config = self.load_config()
        self.models: Dict[str, ModelConfig] = {}
        self.stats = ClientStats()
        self.is_connected = False
        self.host_id = None
        self.running = False
        self.connection_thread = None
        self.status_thread = None
        self.work_thread = None
        self.client_uuid = self.load_or_create_uuid()
        
        try:
            self.openai_client = openai.OpenAI(base_url=self.config['base_api_url'], api_key=self.config['api_key'])
        except Exception as e:
            logger.critical(f"Failed to initialize OpenAI client: {e}. Please check your API Base URL in settings.")
            self.openai_client = None

        self.init_database()
        self.load_models_config()
        self.discover_models()

    def load_models_config(self):
        """Load model configurations from JSON file"""
        if os.path.exists(MODELS_CONFIG_FILE):
            try:
                with open(MODELS_CONFIG_FILE, 'r') as f:
                    models_data = json.load(f)
                for model_name, model_data in models_data.items():
                    self.models[model_name] = ModelConfig(
                        name=model_name,
                        enabled=model_data.get('enabled', False),
                        supports_embedding=model_data.get('supports_embedding', False),
                        supports_vision=model_data.get('supports_vision', False),
                        supports_audio=model_data.get('supports_audio', False),
                        max_concurrent=model_data.get('max_concurrent', 2),
                        context_length=model_data.get('context_length', 4096),
                        quantization=model_data.get('quantization', 'unknown')
                    )
                logger.info(f"Loaded {len(self.models)} model configurations from file")
            except Exception as e:
                logger.error(f"Error loading models config: {e}")

    def save_models_config(self):
        """Save model configurations to JSON file"""
        try:
            models_data = {}
            for model_name, model in self.models.items():
                models_data[model_name] = {
                    'enabled': model.enabled,
                    'supports_embedding': model.supports_embedding,
                    'supports_vision': model.supports_vision,
                    'supports_audio': model.supports_audio,
                    'max_concurrent': model.max_concurrent,
                    'context_length': model.context_length,
                    'quantization': model.quantization
                }
            with open(MODELS_CONFIG_FILE, 'w') as f:
                json.dump(models_data, f, indent=2)
            logger.info(f"Saved {len(self.models)} model configurations to file")
        except Exception as e:
            logger.error(f"Error saving models config: {e}")

    def load_config(self) -> dict:
        # Only use these as fallbacks if config file doesn't exist
        default_config = {
            'andy_api_url': DEFAULT_ANDY_API_URL, 
            'base_api_url': DEFAULT_API_BASE, 
            "client_name": "Unnamed Client",
            "flask_port": 5000,
            "auto_connect": False,
            "report_interval": 30,
            "max_vram_gb": 0,
            "api_key": ""
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f: 
                    config = json.load(f)
                # Only add missing keys from defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
            except Exception as e: 
                logger.error(f"Error loading config: {e}")
                config = default_config.copy()
        else:
            config = default_config.copy()
        
        # Environment variables can still override
        if 'ANDY_API_URL' in os.environ: config['andy_api_url'] = os.environ['ANDY_API_URL']
        if 'BASE_API_URL' in os.environ: config['base_api_url'] = os.environ['BASE_API_URL']
        if 'API_KEY' in os.environ: config['api_key'] = os.environ['API_KEY']
        if 'FLASK_PORT' in os.environ: config['flask_port'] = int(os.environ['FLASK_PORT'])

        logger.info(f"Using Andy API URL: {config['andy_api_url']}")
        logger.info(f"Using Base API URL: {config['base_api_url']}")
        return config

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f: 
                json.dump(self.config, f, indent=2)
            self.openai_client = openai.OpenAI(base_url=self.config['base_api_url'], api_key=self.config['api_key'])
            logger.info("OpenAI client re-initialized with new settings.")
        except Exception as e: 
            logger.error(f"Error saving config or re-initializing client: {e}")

    def init_database(self):
        try:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        model_name TEXT, request_type TEXT, tokens INTEGER, response_time REAL, success BOOLEAN
                    )
                ''')
        except Exception as e: logger.error(f"Database initialization error: {e}")

    def discover_models(self):
        if not self.openai_client:
            logger.error("Cannot discover models: OpenAI client is not initialized.")
            return
        try:
            models_response = self.openai_client.models.list(timeout=10)
            current_models = set(self.models.keys())
            discovered_models = set()
            
            for model_data in models_response:
                model_name = model_data.id
                discovered_models.add(model_name)
                is_embedding_model = "embed" in model_name.lower()
                
                if model_name not in self.models:
                    # Create new model with default settings
                    self.models[model_name] = ModelConfig(name=model_name, enabled=False, supports_embedding=is_embedding_model)
                else:
                    # Update existing model's embedding capability if needed
                    if not self.models[model_name].supports_embedding and is_embedding_model:
                        self.models[model_name].supports_embedding = True
            
            # Remove models that are no longer available
            for model_name in current_models - discovered_models:
                if model_name in self.models: 
                    del self.models[model_name]

            # Save updated model configurations
            self.save_models_config()
            logger.info(f"Discovered {len(self.models)} models from the endpoint.")
        except openai.APIConnectionError as e:
            logger.error(f"Failed to discover models: Could not connect to API endpoint at {self.config['base_api_url']}.")
        except Exception as e: 
            logger.error(f"Error discovering models: {e}")

    def load_or_create_uuid(self):
        if os.path.exists(UUID_FILE):
            with open(UUID_FILE, 'r') as f: return f.read().strip()
        new_uuid = str(uuid.uuid4())
        with open(UUID_FILE, 'w') as f: f.write(new_uuid)
        return new_uuid

    def connect_to_pool(self):
        if self.is_connected:
            logger.info("Already connected.")
            return True

        config = self.load_config()
        enabled_models = [asdict(model) for model in self.models.values() if model.enabled]
        if not enabled_models:
            logger.error("Cannot connect: No models are enabled.")
            return False

        client_capabilities = set()
        for model in self.models.values():
            if model.enabled:
                if not model.supports_embedding or model.supports_vision or model.supports_audio:
                    client_capabilities.add('text')
                if model.supports_embedding: client_capabilities.add('embedding')
                if model.supports_vision: client_capabilities.add('vision')
                if model.supports_audio: client_capabilities.add('audio')
        
        if not client_capabilities and enabled_models:
            client_capabilities.add('text')

        payload = {
            'info': {
                'models': enabled_models,
                'max_clients': sum(m['max_concurrent'] for m in enabled_models),
                'endpoint': config['base_api_url'],
                'capabilities': list(client_capabilities),
                'vram_total_gb': config.get('max_vram_gb', 0),
                'client_uuid': self.client_uuid,
                'client_name': config.get('client_name', 'Unnamed Client')
            }
        }
        
        try:
            logger.info("Joining the pool...")
            response = requests.post(f"{config['andy_api_url']}/api/join_pool", json=payload, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to join pool: {response.status_code} - {response.text}")
                return False

            response_data = response.json()
            received_host_id = response_data.get('host_id')
            if not received_host_id:
                logger.error("Failed to connect: Server did not provide a host_id.")
                return False

            logger.info(f"Received host_id: {received_host_id}. Verifying connection...")
            for i in range(3): # Verification loop
                time.sleep(0.5 + i * 0.5)
                ping_payload = {'host_id': received_host_id, 'current_load': 0, 'status': 'active'}
                try:
                    ping_response = requests.post(f"{config['andy_api_url']}/api/ping_pool", json=ping_payload, timeout=5)
                    if ping_response.status_code == 200:
                        logger.info(f"Connection verified on attempt {i+1}.")
                        self.host_id = received_host_id
                        self.is_connected = True
                        return True
                    logger.warning(f"Ping verification attempt {i+1} failed with status {ping_response.status_code}.")
                except requests.RequestException as ping_e:
                    logger.warning(f"Ping verification attempt {i+1} failed with network error: {ping_e}.")
            
            logger.error("Failed to verify connection. Aborting.")
            return False

        except Exception as e:
            logger.error(f"Error during connection process: {e}", exc_info=True)
            return False

    def disconnect_from_pool(self):
        if not self.is_connected or not self.host_id:
            self.is_connected = False
            self.host_id = None
            return True
        try:
            requests.post(f"{self.config['andy_api_url']}/api/leave_pool", json={'host_id': self.host_id}, timeout=10)
            logger.info(f"Successfully disconnected (host_id: {self.host_id})")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
        finally:
            self.is_connected = False
            self.host_id = None
        return True

    def report_status(self):
        if not self.is_connected or not self.host_id: return
        try:
            payload = {'host_id': self.host_id, 'current_load': 0, 'status': 'active'}
            response = requests.post(f"{self.config['andy_api_url']}/api/ping_pool", json=payload, timeout=10)
            if response.status_code == 404:
                logger.warning(f"Host not found in pool, marking as disconnected.")
                self.is_connected = False
                self.host_id = None
        except Exception as e:
            logger.error(f"Error pinging pool: {e}")

    def start_background_threads(self):
        if self.running: return
        self.running = True
        self.connection_thread = threading.Thread(target=self._connection_loop, daemon=True)
        self.status_thread = threading.Thread(target=self._status_loop, daemon=True)
        self.work_thread = threading.Thread(target=self._work_polling_loop, daemon=True)
        self.connection_thread.start()
        self.status_thread.start()
        self.work_thread.start()
        logger.info("Background threads started")

    def stop_background_threads(self):
        self.running = False
        logger.info("Background threads stopped")

    def _connection_loop(self):
        time.sleep(2) # Initial delay before first check
        while self.running:
            if self.config.get('auto_connect') and not self.is_connected:
                logger.info("Auto-connect is ON. Attempting to connect to pool...")
                try:
                    self.connect_to_pool()
                except Exception as e:
                    logger.error(f"Error during auto-reconnection attempt: {e}")
            time.sleep(30) # Check every 30 seconds

    def _status_loop(self):
        while self.running:
            if self.is_connected:
                self.report_status()
            time.sleep(self.config.get('report_interval', 30))

    def _work_polling_loop(self):
        logger.info("Work polling thread started")
        while self.running:
            if self.is_connected and self.host_id:
                try:
                    enabled_models = [model.name for model in self.models.values() if model.enabled]
                    if not enabled_models:
                        time.sleep(10)
                        continue
                    
                    payload = {"host_id": self.host_id, "models": enabled_models, "timeout": 30}
                    response = requests.post(f"{self.config['andy_api_url']}/api/poll_for_work", json=payload, timeout=35)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('has_work') and result.get('work_item'):
                            work_data = result['work_item']
                            work_id = work_data.get('work_id')
                            logger.info(f"Received work: {work_id} for model {work_data.get('model')}")
                            threading.Thread(target=self.process_work, args=(work_id, work_data)).start()
                    elif response.status_code == 404:
                        logger.warning("Host not registered, marking as disconnected.")
                        self.is_connected = False
                        self.host_id = None
                except requests.exceptions.RequestException as e:
                    logger.error(f"Polling request exception: {e}")
                except Exception as e:
                    logger.error(f"Work polling error: {e}", exc_info=True)
                    time.sleep(5)
            else:
                time.sleep(5)

    def process_work(self, work_id: str, work_data: dict):
        logger.info(f"--- Starting to process work {work_id} ---")
        if not self.openai_client:
            self.submit_work_error(work_id, "OpenAI client not configured")
            return

        start_time = time.time()
        model_name = work_data.get('model')
        work_type = work_data.get('work_type', 'chat')

        try:
            if model_name not in self.models or not self.models[model_name].enabled:
                logger.error(f"Model {model_name} not available or not enabled for work {work_id}.")
                self.submit_work_error(work_id, f"Model {model_name} not available")
                return
            
            logger.info(f"Processing work {work_id} of type '{work_type}' for model '{model_name}'.")

            result_payload = None
            if work_type == 'embedding':
                api_response = self.openai_client.embeddings.create(
                    model=model_name,
                    input=work_data.get('input', ''),
                    timeout=120
                )
                result_payload = {"embedding": api_response.data[0].embedding}
            else: # Default to 'chat'
                api_response = self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=work_data['messages'],
                    stream=False,
                    timeout=120,
                    **work_data.get('params', {})
                )
                
                result_payload = {
                    'message': {
                        'role': api_response.choices[0].message.role,
                        'content': api_response.choices[0].message.content
                    },
                    'model': api_response.model,
                    'usage': api_response.usage.dict() if hasattr(api_response.usage, 'dict') else {
                        'prompt_tokens': api_response.usage.prompt_tokens,
                        'completion_tokens': api_response.usage.completion_tokens,
                        'total_tokens': api_response.usage.total_tokens
                    },
                    'eval_count': api_response.usage.completion_tokens if hasattr(api_response.usage, 'completion_tokens') else 0
                }

            response_time = time.time() - start_time
            logger.info(f"API request for work {work_id} completed in {response_time:.2f}s.")
            
            self.submit_work_result(work_id, result_payload)
            tokens = result_payload.get('usage', {}).get('completion_tokens', 0) if work_type == 'chat' else 0
            self.log_request(model_name, work_type, tokens, response_time, True)

        except openai.APIError as e:
            error_msg = f"API request failed: {e}"
            logger.error(f"API error for work {work_id}: {error_msg}", exc_info=True)
            self.submit_work_error(work_id, error_msg)
            self.log_request(model_name, work_type, 0, time.time() - start_time, False)
        except Exception as e:
            logger.error(f"Error processing work {work_id}: {e}", exc_info=True)
            self.submit_work_error(work_id, str(e))
            self.log_request(model_name, work_type, 0, time.time() - start_time, False)

        logger.info(f"--- Finished processing work {work_id} ---")

    def submit_work_result(self, work_id: str, result: dict):
        logger.info(f"Submitting result for work {work_id}...")
        try:
            payload = {"work_id": work_id, "result": result}
            response = requests.post(f"{self.config['andy_api_url']}/api/submit_work_result", json=payload, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to submit result for work {work_id}. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            logger.error(f"Error submitting work result for {work_id}: {e}", exc_info=True)

    def submit_work_error(self, work_id: str, error: str):
        logger.info(f"Submitting error for work {work_id}: {error}")
        try:
            payload = {"work_id": work_id, "error": error}
            response = requests.post(f"{self.config['andy_api_url']}/api/submit_work_result", json=payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to submit error for work {work_id}. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            logger.error(f"Error submitting work error for {work_id}: {e}", exc_info=True)

    def log_request(self, model_name: str, request_type: str, tokens: int, response_time: float, success: bool):
        try:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute(
                    "INSERT INTO requests (model_name, request_type, tokens, response_time, success) VALUES (?, ?, ?, ?, ?)", 
                    (model_name, request_type, tokens, response_time, success)
                )
            self.stats.total_requests += 1
            if success:
                self.stats.successful_requests += 1
            else:
                self.stats.failed_requests += 1
            self.stats.total_tokens += tokens
            self.stats.last_request_time = datetime.now()
        except Exception as e:
            logger.error(f"Error logging request: {e}")

# --- Initialize Client ---
client = LocalClient()

# --- Flask Routes ---
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index():
    return render_template('index.html', models=client.models, stats=asdict(client.stats), config=client.config, is_connected=client.is_connected, host_id=client.host_id)

@app.route('/models')
def models_page():
    return render_template('models.html', models=client.models, config=client.config)

@app.route('/metrics')
def metrics_page():
    uptime_seconds = (datetime.now() - client.stats.uptime_start).total_seconds()
    return render_template('metrics.html', models=client.models, stats=asdict(client.stats), config=client.config, uptime_hours=f"{uptime_seconds / 3600:.1f}")

@app.route('/settings')
def settings_page():
    return render_template('settings.html', config=client.config, is_connected=client.is_connected, models=client.models)

# --- API Endpoints ---
@app.route('/api/models/<path:model_name>/toggle', methods=['POST'])
def toggle_model(model_name):
    model_name = unquote(model_name)
    if model_name in client.models:
        client.models[model_name].enabled = not client.models[model_name].enabled
        client.save_models_config()  # Save to file
        logger.info(f"Model {model_name} {'enabled' if client.models[model_name].enabled else 'disabled'}")
        return jsonify({'success': True, 'enabled': client.models[model_name].enabled})
    return jsonify({'success': False, 'error': 'Model not found'}), 404

@app.route('/api/models/<path:model_name>/config', methods=['POST'])
def update_model_config(model_name):
    model_name = unquote(model_name)
    if model_name not in client.models:
        return jsonify({'success': False, 'error': 'Model not found'}), 404
    data = request.get_json()
    model = client.models[model_name]
    for key in ['max_concurrent', 'context_length', 'supports_embedding', 'supports_vision', 'supports_audio']:
        if key in data:
            setattr(model, key, data[key])
    client.save_models_config()  # Save to file
    logger.info(f"Updated config for model {model_name}")
    return jsonify({'success': True})

@app.route('/api/discover_models', methods=['POST'])
def discover_models_endpoint():
    client.discover_models()
    return jsonify({'success': True, 'model_count': len(client.models)})

@app.route('/api/connect', methods=['POST'])
def connect():
    if client.connect_to_pool():
        return jsonify({'success': True, 'host_id': client.host_id})
    return jsonify({'success': False, 'error': 'Failed to connect'}), 500

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    if client.disconnect_from_pool():
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Failed to disconnect'}), 500

@app.route('/api/save_config', methods=['POST'])
def save_config_endpoint():
    data = request.get_json()
    client.config.update(data)
    client.save_config()
    logger.info("Configuration saved")
    return jsonify({'success': True})

@app.route('/api/status')
def status():
    return jsonify({
        'is_connected': client.is_connected,
        'host_id': client.host_id,
        'running': client.running,
        'enabled_models': [name for name, model in client.models.items() if model.enabled]
    })

@app.route('/api/test_connections', methods=['POST'])
def test_connections():
    """Test connections to both the OpenAI-compatible endpoint and Andy API"""
    data = request.get_json() or {}
    api_base = data.get('base_api_url', client.config.get('base_api_url'))
    api_key = data.get('api_key', client.config.get('api_key'))
    andy_url = data.get('andy_api_url', client.config.get('andy_api_url'))
    
    results = {
        'endpoint_ok': False,
        'endpoint_error': '',
        'andy_ok': False,
        'andy_error': '',
        'models_count': 0
    }
    
    # Test OpenAI-compatible endpoint
    try:
        temp_client = openai.OpenAI(base_url=api_base, api_key=api_key)
        models_response = temp_client.models.list(timeout=10)
        results['endpoint_ok'] = True
        results['models_count'] = len(list(models_response.data))
    except openai.APIConnectionError as e:
        results['endpoint_error'] = f"Connection failed: {str(e)}"
    except openai.AuthenticationError as e:
        results['endpoint_error'] = f"Authentication failed: {str(e)}"
    except Exception as e:
        results['endpoint_error'] = f"Error: {str(e)}"
    
    # Test Andy API
    try:
        response = requests.get(f"{andy_url}/api/v1/models", timeout=10)
        if response.status_code == 200:
            results['andy_ok'] = True
    except requests.exceptions.ConnectionError as e:
        results['andy_error'] = f"Connection failed: {str(e)}"
    except requests.exceptions.Timeout as e:
        results['andy_error'] = f"Timeout: {str(e)}"
    except Exception as e:
        results['andy_error'] = f"Error: {str(e)}"
    
    return jsonify(results)

# --- Main Execution ---
if __name__ == '__main__':
    port = client.config.get('flask_port', client.config.get('flask_port'))
    client.start_background_threads()
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    finally:
        logger.info("Shutting down...")
        client.stop_background_threads()
        client.disconnect_from_pool()
