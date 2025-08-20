# GAE252_AI_SIEM: AI-Powered Security Information and Event Management

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An AI-powered SIEM (Security Information and Event Management) system designed to proactively detect, analyze, and respond to cybersecurity threats. This project leverages Large Language Models (LLMs) to analyze logs, identify potential security incidents, and generate insightful reports.

## 🚀 Overview

In today's complex digital landscape, manually analyzing security logs is a daunting and time-consuming task. GAE252_AI_SIEM automates this process by using an AI agent to intelligently analyze logs from various sources. The system can identify a wide range of cyberattacks, including DDoS, SQL Injection, and Path Traversal, and provide detailed reports to security teams.

## ✨ Features

*   **AI-Powered Threat Detection:** Utilizes LLMs to analyze logs and identify suspicious activities.
*   **Automated Reporting:** Generates detailed and easy-to-understand reports for security incidents.
*   **Multi-Component Architecture:** A modular and scalable system with components for AI analysis, messaging, and data storage.
*   **Cloud-Ready Deployment:** Includes deployment configurations for GCP.
*   **Containerized:** Uses Docker and Docker Compose for easy setup and deployment.
*   **Extensible:** Designed to be easily extended with new detection capabilities and integrations.

## 🛠️ Tech Stack

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-%234ea94b.svg?style=for-the-badge&logo=mongodb&logoColor=white)
![Qdrant](https://img.shields.io/badge/qdrant-%23E62F2B.svg?style=for-the-badge&logo=qdrant&logoColor=white)
![GCP](https://img.shields.io/badge/GCP-%234285F4.svg?style=for-the-badge&logo=google-cloud&logoColor=white)
![Slack](https://img.shields.io/badge/Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white)

## 🏛️ Architecture

The system is composed of several microservices that work together to provide a comprehensive security solution.

...

*   **AIAgent:** The core component that analyzes logs, generates reports, and interacts with other services.
*   **MsgCenter:** Handles messaging and notifications.
*   **Qdrant:** A vector database for storing and searching log embeddings.
*   **RPA:** A Robotic Process Automation component for automating tasks.
*   **MongoDB:** Used for storing reports and other system data.

## 🏁 Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   [Docker](https://docs.docker.com/get-docker/)
*   [Python 3.12](https://www.python.org/downloads/)
*   [Qdrant](https://qdrant.tech/documentation/quickstart/)
*   [MongoDB](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-community-with-docker/)
*   [Ollama](https://ollama.com/)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/GAE252_AI_SIEM.git
    cd GAE252_AI_SIEM
    ```

2.  **Initial Configuration:**
    *   Run the `StartupConfig.py` script to generate `config.ini` and create tables in the vector database:
        ```bash
        python StartupConfig.py
        ```

3.  **Deployment:**
    *   Run the `StartupDeploy.py` script to deploy the project locally, on-premise, or to the cloud.
        ```bash
        python StartupDeploy.py
        ```
    *   The script will guide you through the deployment options.

## ☁️ Deployment

The `StartupDeploy.py` script provides a convenient way to deploy the application to different environments.

### Local/On-Premise Deployment

1.  Run `python StartupDeploy.py`.
2.  Choose option `a` for a local test environment or `b` for a Docker on-premise deployment.
3.  The script will configure the endpoints and start the services.

### Cloud Deployment (GCP)

1.  **Prerequisites:**
    *   Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install).
    *   Log in to your cloud provider using `gcloud auth login`. The detailed instructions refer to the `glcoud_init.md` in `Deployment/gcp` directory.

2.  **Run the deployment script:**
    ```bash
    python StartupDeploy.py
    ```

3.  **Choose your cloud provider:**
    *   Select option `c` for Public Cloud.
    *   Choose your desired cloud provider (GCP).

4.  **Follow the prompts:**
    *   The script will guide you through the process of configuring your deployment, including setting up necessary resources like artifact registry, cloud storage and cloud run in GCP.

## Usage

Once the services are running, you can start analyzing logs.

**Use the API:** The AIAgent exposes an API for programmatic access. You can explore the API endpoints using the Swagger UI at `http://localhost:10001/docs`.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m '''Add some AmazingFeature'''`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
