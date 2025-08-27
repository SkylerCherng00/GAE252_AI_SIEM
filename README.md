# GAE252_AI_SIEM: AI-Powered Security Information and Event Management

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

An intelligent AI-powered SIEM (Security Information and Event Management) system that leverages Large Language Models (LLMs) and vector databases to automatically detect, analyze, and respond to cybersecurity threats. The system provides real-time log analysis, automated threat detection, and comprehensive security reporting with multi-language support.

## 🚀 Overview

GAE252_AI_SIEM transforms traditional security monitoring by combining AI-driven analysis with modern microservices architecture. The system intelligently processes security logs from various sources, identifies potential threats using MITRE ATT&CK and OWASP frameworks, and generates detailed security reports. With support for multiple LLM providers and automated response capabilities, it provides comprehensive security coverage for modern infrastructure.

## ✨ Key Features

### 🤖 AI-Powered Security Analysis
- **Multi-LLM Support**: Compatible with Azure OpenAI, Ollama, and Gemini
- **Intelligent Threat Detection**: Identifies DDoS attacks, SQL injection, path traversal, and other OWASP Top 10 threats
- **Vector-Based Log Search**: Uses Qdrant for efficient similarity search and pattern matching
- **Multi-language Reports**: Generates security reports in English and Traditional Chinese

### 🏗️ Microservices Architecture
- **AIAgent**: Core analysis engine with FastAPI interface
- **MsgCenter**: Centralized messaging and notification hub
- **Qdrant**: Vector database for log embeddings and similarity search
- **RPA**: Automated response and Slack/Teams integration
- **MongoDB**: Persistent storage for reports and system data

### 🚀 Deployment Flexibility
- **Local Development**: Docker Compose setup for testing
- **On-Premise**: Production-ready containerized deployment
- **Cloud-Native**: GCP App Engine and Cloud Run support
- **Auto-Configuration**: Intelligent setup scripts for quick deployment

### 🔒 Security-First Design
- **MITRE ATT&CK Framework**: Structured threat classification
- **OWASP Compliance**: Industry-standard security practices
- **Automated Response**: Real-time alert generation and team notifications
- **Audit Trail**: Complete log analysis and decision tracking

## 🛠️ Technology Stack

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-%234ea94b.svg?style=for-the-badge&logo=mongodb&logoColor=white)
![Qdrant](https://img.shields.io/badge/qdrant-%23E62F2B.svg?style=for-the-badge&logo=qdrant&logoColor=white)
![GCP](https://img.shields.io/badge/GCP-%234285F4.svg?style=for-the-badge&logo=google-cloud&logoColor=white)
![Slack](https://img.shields.io/badge/Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white)

## 🏛️ System Architecture

```
                        ┌─────────────────┐
                        │   MsgCenter     │
                        │(Store Crdential)│
                        └─────────────────┘
                                 ▲
                                 │
┌─────────────────┐    ┌─────────┴───────┐
│   Log Sources   │───▶│   AIAgent       │
│                 │    │   (Analysis)    │
└─────────────────┘    └─┬───┬───┬───┬───┘
                          │   │   │   │
                          ▼   ▼   ▼   ▼
            ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
            │   Qdrant        │  │   MongoDB       │  │      RPA        │
            │  (Vector DB)    │  │   (Storage)     │  │ (Automation)    │
            └─────────────────┘  └─────────────────┘  └─────────┬───────┘
                                                                │
                                                                ▼
                                                      ┌─────────────────┐
                                                      │ Slack/Teams     │
                                                      │ (Notifications) │
                                                      └─────────────────┘
```

### Data Flow & Processing Pipeline

**1. Log Ingestion & Initial Processing**
- **Input**: Security logs from various sources (web servers, firewalls, applications)
- **AIAgent** receives raw log data via REST API endpoints
- **Purpose**: Centralized entry point for all security log analysis

**2. AI-Powered Threat Analysis**
- **AIAgent** uses LLMs to analyze log patterns and identify potential threats
- **Vector Search**: Queries Qdrant for similar security incidents and SOPs
- **Purpose**: Intelligent threat detection using ML models and historical data

**3. Contextual Enhancement**
- **Qdrant** provides semantic search capabilities for security documentation
- Retrieves relevant SOPs, security criteria, and communication protocols
- **Purpose**: Enrich analysis with organizational security knowledge

**4. Report Generation & Storage**
- **AIAgent** generates detailed security reports with threat classifications
- **MongoDB** stores analysis results, reports, and audit trails
- **Purpose**: Persistent storage for compliance and forensic analysis

**5. Automated Response & Notification**
- **MsgCenter** routes security alerts to appropriate response teams
- **RPA** automates predefined response actions and escalation procedures
- **Purpose**: Immediate threat response and team coordination

**6. Team Communication**
- **Slack/Teams Integration** sends real-time notifications to security teams
- Includes threat severity, recommended actions, and incident details
- **Purpose**: Ensure rapid human response to critical security events

### Core Components

- **AIAgent** (`AIAgent/`): FastAPI-based analysis engine that processes logs using LLMs and generates security reports
- **MsgCenter** (`MsgCenter/`): Centralize and manage credentials and configurations
- **Qdrant** (`Qrant/`): Vector database storing document embeddings for semantic log search and contextual analysis
- **RPA** (`Rpa/`): Robotic Process Automation for automated responses and team notifications
- **MongoDB**: Document storage for security reports, incident history, and audit trails
- **Configuration Templates** (`ConfigTemplate/`): Pre-configured templates for different deployment scenarios

## 🚀 Quick Start

### Prerequisites

**Required Software:**
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Python 3.12+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

**External Services (Choose one LLM provider):**
- [Ollama](https://ollama.com/) (Local LLM)
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) (Cloud LLM)
- [Google Gemini](https://ai.google.dev/) (Cloud LLM)

**Databases:**
- [Qdrant](https://qdrant.tech/) (Vector database)
- [MongoDB](https://www.mongodb.com/) (Document storage)

### Installation
0. **Create Virtual Environment and Activate**

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/GAE252_AI_SIEM.git
   cd GAE252_AI_SIEM
   ```

2. **Configure the System**
   ```bash
   python StartupConfig.py
   ```
   This interactive script will:
   - Generate configuration files for all services
   - Validate your LLM provider settings
   - Set up database connections
   - Configure messaging integrations (Slack/Teams)

3. **Initialize Vector Database**
   ```bash
   # Install packages
   pip install -r ./Qdrant/requirement.txt
   
   # Place your security documentation in Qrant/src/
   cp your-security-docs/* Qrant/src/
   
   # Initialize Qdrant with your documents
   python StartupConfig.py
   # Select option 2: "Initialize Qdrant database"
   ```

4. **Deploy the System**
   ```bash
   python StartupDeploy.py
   ```
   Choose your deployment option:
   - **Local Testing** (`a`): Development environment
   - **Docker On-Premise** (`b`): Production containerized deployment
   - **Cloud Deployment** (`c`): GCP App Engine/Cloud Run

## 📋 Configuration Guide

### LLM Provider Setup

**Option 1: Ollama (Local)**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull llama3.1
ollama pull nomic-embed-text
```

**Option 2: Azure OpenAI**
- Obtain API key and endpoint from Azure Portal
- Configure in `StartupConfig.py` during setup

**Option 3: Google Gemini**
- Get API key from Google AI Studio
- Configure in `StartupConfig.py` during setup

### Database Setup

**Qdrant Vector Database:**
```bash
# Using Docker (recommended)
docker run -p 6333:6333 qdrant/qdrant
```

**MongoDB:**
```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

## 🚀 Deployment Options

### 1. Local Development
```bash
python StartupDeploy.py
# Select option 'a' - Local test environment
```
Services will be available at:
- AIAgent API: http://localhost:10001
- API Documentation: http://localhost:10001/docs

### 2. Docker Production
```bash
python StartupDeploy.py
# Select option 'b' - Docker on-premise deployment
```
Uses `docker-compose.yml` for orchestrated deployment.

### 3. Cloud Deployment (GCP)
```bash
# Prerequisites
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Deploy
python StartupDeploy.py
# Select option 'c' - Public Cloud
```

## 💡 Usage Examples

### API Usage

**Analyze Security Logs:**
```bash
curl -X POST "http://localhost:10001/analyze_logs" \
  -H "Content-Type: application/json" \
  -d '{
    "logs": "192.168.1.100 - - [01/Jan/2024:12:00:00] \"GET /admin/../../etc/passwd HTTP/1.1\" 404 -",
    "language": "en"
  }'
```

**Upload Log File:**
```bash
curl -X POST "http://localhost:10001/upload_logs" \
  -F "file=@security_logs.txt" \
  -F "language=en"
```

### Web Interface

Access the interactive API documentation at:
```
http://localhost:10001/docs
```

### Integration Examples

**Slack Notifications:**
Configure in `config_rpa.ini` to receive real-time security alerts in your Slack channels.

**Automated Response:**
The RPA component can automatically escalate critical threats to your security team.

## 📁 Project Structure

```
GAE252_AI_SIEM/
├── AIAgent/                    # Core AI analysis service
│   ├── agent.py               # Main FastAPI application
│   ├── sysmsg/                # System prompts for different analysis tasks
│   │   ├── LogAnalyzer.txt    # Security log analysis prompts
│   │   ├── LogPreviewer.txt   # Log preview and filtering prompts
│   │   └── QuickRespTeam.txt  # Incident response prompts
│   └── utils/                 # Utility modules
│       ├── factory_llm.py     # LLM provider factory
│       ├── factory_embedding.py # Embedding model factory
│       ├── util_mongodb.py    # MongoDB operations
│       └── endpoint.py        # API endpoint configurations
├── MsgCenter/                  # Messaging service
│   └── msg_api.py             # Store credential and configurations
├── Qrant/                      # Vector database service
│   ├── qdrant_api.py          # Qdrant API interface
│   ├── qdrant_embed.py        # Document embedding processor
│   └── src/                   # Security documentation
│       ├── SOP.md             # Standard Operating Procedures
│       ├── SecurityCriteria.md # Security evaluation criteria
│       └── ComTable.md        # Communication protocols
├── Rpa/                        # Robotic Process Automation
│   ├── slack.py               # Slack integration
│   └── endpoint.py            # RPA API endpoints
├── ConfigTemplate/             # Configuration templates
│   ├── config_embed.ini.example    # Embedding configuration
│   ├── config_factory.ini.example  # LLM factory configuration
│   ├── config_mongodb.ini.example  # MongoDB configuration
│   └── config_rpa.ini.example      # RPA configuration
├── Deployment/                 # Cloud deployment configurations
│   └── gcp/                   # Google Cloud Platform
│       ├── service.yaml.example    # App Engine configuration
│       └── gcloud_init.md         # GCP setup instructions
├── StartupConfig.py           # Interactive configuration script
├── StartupDeploy.py          # Deployment automation script
└── docker-compose.yml        # Local container orchestration
```

## 🔧 Configuration Files

The system uses multiple configuration files for different components:

| File | Purpose | Key Settings |
|------|---------|--------------|
| `config_embed.ini` | Embedding configuration | LLM provider, model selection, Qdrant settings |
| `config_factory.ini` | LLM factory settings | API keys, endpoints, model parameters |
| `config_mongodb.ini` | Database configuration | Connection strings, database names |
| `config_rpa.ini` | Automation settings | Slack/Teams tokens, notification settings |

## 🚨 Security Considerations

### Threat Detection Capabilities

The system is designed to detect various security threats including:

- **OWASP Top 10 Threats**
  - SQL Injection
  - Cross-Site Scripting (XSS)
  - Path Traversal
  - Authentication Bypasses
  - Insecure Direct Object References

- **Network Attacks**
  - DDoS attacks
  - Port scanning
  - Brute force attacks
  - Suspicious traffic patterns

- **MITRE ATT&CK Framework**
  - Initial Access techniques
  - Persistence mechanisms
  - Privilege Escalation
  - Defense Evasion
  - Credential Access

### Data Privacy

- All log analysis is performed locally or within your configured cloud environment
- No sensitive data is transmitted to external services without explicit configuration
- Supports air-gapped deployment for sensitive environments

## 🔧 Troubleshooting

### Common Issues

**Configuration Problems:**
```bash
# Validate configuration
python StartupConfig.py
# Select option 1: Configure all components
```

**Docker Issues:**
```bash
# Reset Docker environment
docker-compose down
docker system prune -f
docker-compose up --build
```

**Database Connection:**
```bash
# Check Qdrant status
curl http://localhost:6333/health

# Check MongoDB status
docker exec mongodb mongo --eval "db.adminCommand('ismaster')"
```

**LLM Provider Issues:**
- Verify API keys and endpoints in configuration files
- Check network connectivity for cloud providers
- Ensure Ollama is running for local deployment

### Logs and Debugging

- AIAgent logs: Check container logs with `docker logs ai_siem_agent`
- API documentation: Available at `http://localhost:10001/docs`
- Health checks: Use `/health` endpoints on each service

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Set up development environment: `python StartupConfig.py`
4. Make your changes and test thoroughly
5. Submit a pull request

### Code Standards
- Follow PEP 8 for Python code formatting
- Add docstrings to all functions and classes
- Include unit tests for new features
- Update documentation for API changes

### Security Guidelines
- Never commit API keys or sensitive configuration
- Use environment variables for secrets
- Follow secure coding practices
- Report security vulnerabilities privately

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Documentation**: Check this README and inline code documentation
- **Issues**: Report bugs and feature requests via GitHub Issues
- **Discussions**: Join our community discussions for questions and ideas

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) for LLM orchestration
- [Qdrant](https://qdrant.tech/) for vector database technology
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [MITRE ATT&CK](https://attack.mitre.org/) for threat modeling framework
- [OWASP](https://owasp.org/) for security best practices

---

**Built with ❤️ for cybersecurity professionals**
