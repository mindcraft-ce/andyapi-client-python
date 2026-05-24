# Andy API Local Client

> [!CAUTION]
> **The python local client has been discontinued. Please use the [go local client](https://github.com/mindcraft-ce/andyapi-client-go) instead.**

A modern web-based interface for connecting any OpenAI-compatible AI endpoint to the distributed Andy API compute pool. Share your local AI models and contribute your hardware resources to the network.

## 🚀 Features

*   **Universal Compatibility**: Works with any OpenAI-compatible endpoint including:
    *   **OpenAI API** (https://api.openai.com/v1) - GPT-4, o3, and other OpenAI models
    *   **OpenRouter API** (https://openrouter.ai/api/v1)
    *   **Ollama** (recommended for local models)
    *   **LM Studio**
    *   **Text Generation WebUI (oobabooga)**
    *   **vLLM**
    *   **Any other OpenAI-compatible API server**
*   **Intelligent Web Interface**: A full-featured Flask application with:
    *   **Real-time Dashboard**: Monitor connection status, model activity, and performance metrics
    *   **Model Management**: Enable/disable models, configure capabilities, and adjust settings
    *   **Live Metrics**: View request statistics, success rates, and performance charts
    *   **Connection Testing**: Built-in tools to verify endpoint connectivity
*   **Automatic Model Discovery**: Automatically detects all models available from your endpoint
*   **Advanced Configuration**:
    *   Flexible endpoint configuration with API key support
    *   Client behavior customization (auto-connect, reporting intervals, resource limits)
    *   Persistent settings with environment variable overrides
*   **Pool Integration**:
    *   Seamless registration as a compute host in the Andy API network
    *   Automatic health monitoring and status reporting
    *   Intelligent work polling and job processing
*   **Production Ready**: SQLite database for persistence, background threading, and robust error handling

## 📁 Project Structure

*   **`launch.py`**: Main entry point to start the web interface
*   **`app.py`**: Complete Flask web application with dashboard, model management, and metrics
*   **`requirements.txt`**: Python dependencies for the project
*   **`Dockerfile`**: Docker image definition for secure containerized deployment
*   **`docker-compose.yml`**: Docker Compose configuration for easy container management
*   **`local_client/`**: Configuration and data directory
    *   **`client_config.json`**: Main configuration file for the web interface
*   **`templates/`**: HTML templates for the web interface
    *   **`index.html`**: Main dashboard
    *   **`models.html`**: Model configuration page
    *   **`metrics.html`**: Performance analytics and charts
    *   **`settings.html`**: Configuration interface
*   **`static/`**: Web assets (CSS, JavaScript, favicon)

## 🛠️ Installation & Setup

### Prerequisites

*   **Python 3.8+** (Python 3.12+ recommended for best compatibility)
*   **Any OpenAI-compatible AI server** such as:
    *   **[OpenAI API](https://platform.openai.com/)** - Official OpenAI models (requires API key)
    *   [Ollama](https://ollama.com/) (recommended for local models)
    *   [LM Studio](https://lmstudio.ai/)
    *   [Text Generation WebUI](https://github.com/oobabooga/text-generation-webui)
    *   [vLLM](https://vllm.readthedocs.io/)

### Quick Start

1.  **Clone or Download** this repository to your local machine

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Start Your AI Server** (example with Ollama):
    ```bash
    # Install and start Ollama
    ollama serve
    
    # Pull a model to get started
    ollama pull qwen2.5:7b
    ```

4.  **Launch the Client**:
    ```bash
    python launch.py
    ```

5.  **Access the Web Interface**:
    Open your browser to **http://localhost:5000**

### Docker Deployment

For containerized deployment, you can use either Docker directly or Docker Compose:

**Option 1: Docker Compose (Recommended)**
```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f local_client

# Stop the container
docker-compose down
```

**Option 2: Docker Build & Run**
```bash
# Build the image
docker build -t andy-api-client .

# Run the container
docker run -d \
  --name andy-api-client \
  -p 5000:5000 \
  -v ./local_client:/app/local_client \
  andy-api-client

# View logs
docker logs -f andy-api-client
```

The Docker setup includes:
- **Persistent Configuration**: Your settings in `local_client/` are preserved between container restarts
- **Port Mapping**: Web interface accessible at `http://localhost:5000`
- **Volume Mounting**: Configuration and database files are stored on the host

## 🎮 Using the Interface

### Dashboard
*   **Connection Status**: See if you're connected to the Andy API pool
*   **Quick Actions**: Connect/disconnect with a single click
*   **Model Overview**: View enabled models and their status
*   **Performance Stats**: Monitor total requests, tokens, and success rates

### Model Management
*   **Auto-Discovery**: Refresh to automatically detect available models
*   **Enable/Disable**: Choose which models to share with the pool
*   **Capabilities**: Configure model features (text, embedding, vision, audio)
*   **Settings**: Adjust concurrent requests, context length, and other parameters

### Settings & Configuration
*   **Endpoint Configuration**: Set your AI server URL and API key
*   **Andy API Settings**: Configure connection to the distributed pool
*   **Behavior Options**: Auto-connect, reporting intervals, and resource limits
*   **Connection Testing**: Verify connectivity to both your AI server and Andy API

### Metrics & Analytics
*   **Real-time Charts**: Success rates, request volumes, and performance trends
*   **Historical Data**: Track your contribution over time
*   **System Stats**: Monitor uptime, token processing, and error rates

## ⚙️ Configuration

The client supports multiple configuration methods with the following priority order:

### 1. Environment Variables (Highest Priority)
```bash
# Core endpoint settings
export ANDY_API_URL="https://andy.mindcraft-ce.com"
export BASE_API_URL="http://localhost:11434/v1"
export API_KEY="your-api-key-here"

# Optional web interface settings
export FLASK_PORT="5001"

# Then start the client
python launch.py
```

### 2. Web Interface Settings
Use the **Settings** page in the web interface to configure:
*   **Andy API URL**: Connection to the distributed compute pool
*   **Base API URL**: Your local AI server endpoint (OpenAI-compatible)
*   **API Key**: Authentication for your AI server (if required)
*   **Client Name**: Friendly identifier for your contribution
*   **Auto-Connect**: Automatically join the pool on startup
*   **Report Interval**: How often to send status updates (seconds)
*   **Max VRAM**: Resource limit for your contribution (GB)

### 3. Configuration File (Default)
Edit `local_client/client_config.json`:
```json
{
  "andy_api_url": "https://andy.mindcraft-ce.com",
  "base_api_url": "http://localhost:11434/v1",
  "client_name": "My AI Server",
  "flask_port": 5000,
  "auto_connect": false,
  "report_interval": 30,
  "max_vram_gb": 0,
  "api_key": ""
}
```

### Common Endpoint Configurations

**OpenAI API (Official)**:
```
Base API URL: https://api.openai.com/v1
API Key: sk-... (required - get from https://platform.openai.com/api-keys)
```

**OpenRouter API**:
```
Base API URL: https://openrouter.ai/api/v1
API Key: sk-... (required - get from https://openrouter.ai/settings/keys)
```

**Ollama (Default)**:
```
Base API URL: http://localhost:11434/v1
API Key: ollama (or leave empty)
```

**LM Studio**:
```
Base API URL: http://localhost:1234/v1
API Key: lm-studio (or as configured)
```

**Text Generation WebUI**:
```
Base API URL: http://localhost:5000/v1
API Key: (as configured in your setup)
```

## 🔧 Troubleshooting

### Connection Issues

**Cannot Connect to AI Server**:
*   Verify your AI server is running (e.g., `ollama serve` for Ollama)
*   Test the endpoint: `curl http://localhost:11434/v1/models`
*   Check the Base API URL in Settings matches your server
*   Ensure API key is correct if your server requires authentication

**Cannot Connect to Andy API**:
*   Check your internet connection and firewall settings
*   Verify the Andy API URL: `https://andy.mindcraft-ce.com`
*   Test connectivity: `curl https://andy.mindcraft-ce.com/api/v1/models`

### Port Conflicts

**"Port Already in Use" Error**:
*   Another application is using port 5000
*   Change the port in Settings or use environment variable:
    ```bash
    export FLASK_PORT=5001
    python launch.py
    ```

### Model Issues

**No Models Found**:
*   Ensure your AI server has models loaded/downloaded
*   For Ollama: `ollama list` to see available models
*   Use the "Refresh Models" button in the Models page
*   Check the Base API URL is correct and accessible

**Models Not Processing Requests**:
*   Verify models are enabled in the Models page
*   Check model configuration (max concurrent requests, context length)
*   Review the Metrics page for error details

### Performance Issues

**Slow Response Times**:
*   Reduce concurrent requests per model in Model settings
*   Check your hardware resources (RAM, VRAM, CPU)
*   Consider adjusting the `max_vram_gb` setting

**High Error Rates**:
*   Monitor the Metrics page for failure patterns
*   Check model context length limits
*   Verify your AI server isn't overloaded

### Data & Logs

**Reset Configuration**:
*   Delete `local_client/client_config.json` to restore defaults
*   Use "Reset to Defaults" button in Settings

**View Detailed Logs**:
*   Check the terminal/console output where you started the client
*   Logs include connection status, model discovery, and error details

## 🚀 Getting Started Checklist

1. ✅ **Install Python 3.8+** and run `pip install -r requirements.txt`
2. ✅ **Set up your AI server** (Ollama, LM Studio, etc.) and ensure it's running
3. ✅ **Download/load at least one model** in your AI server
4. ✅ **Start the client** with `python launch.py`
5. ✅ **Open the web interface** at `http://localhost:5000`
6. ✅ **Configure settings** on the Settings page (if needed)
7. ✅ **Enable models** you want to share on the Models page
8. ✅ **Connect to the pool** from the Dashboard
9. ✅ **Monitor your contribution** on the Metrics page

## 💡 Tips for Optimal Performance

*   **Model Selection**: Enable models that match your hardware capabilities
*   **Concurrent Requests**: Start with 1-2 concurrent requests per model and adjust based on performance. For external APIs (such as OpenAI), this could be up to the context length limit (e.g. 128,000 concurrent requests for GPT-4o-mini)
*   **Resource Monitoring**: Keep an eye on RAM/VRAM usage and adjust `max_vram_gb` if needed
*   **Network Stability**: Ensure a stable internet connection for consistent pool participation
*   **Regular Updates**: Check for updates to both the Andy API client and your AI server software

---

**Need Help?** Check the troubleshooting section above or visit the [Andy API documentation](https://andy.mindcraft-ce.com) for more information.
