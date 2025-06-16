# Frankie AI Web Agent

**Frankie** is a sophisticated, self-hostable, full-stack web application designed to function as an extensible AI assistant. It integrates seamlessly with Large Language Models (LLMs) via local or remote Ollama instances. Beyond basic chat, Frankie boasts advanced capabilities including AI-powered self-code modification (under strict administrator supervision), a robust plugin system for extending its functionalities, and a specialized Genealogy Research Agent to help users explore their family history.

Built with a modern technology stack (FastAPI, React, Docker, Caddy) and a focus on security and modularity, Frankie is designed for ease of development, deployment, and ongoing evolution.

## ✨ Features

Frankie comes packed with a wide array of features:

* **Core Application & User Experience:**
    * **FastAPI Backend**: Robust, high-performance Python backend.
    * **React Frontend**: Dynamic and responsive UI built with Vite and Tailwind CSS.
    * **Ollama Integration**: Connects to local or remote Ollama servers for LLM inference.
    * **User Authentication**: Secure JWT-based registration, login, and session management.
    * **Role-Based Access Control**: Differentiates between `admin` and `user` roles.
    * **Chat Interface**: Interactive chat with LLMs, including model selection and Markdown rendering for AI responses.
    * **Chat History**: Persistent storage and retrieval of user chat interactions.
    * **Persistent Storage**: Uses SQLite by default for all application data, persisted via Docker volumes. Alembic is used for database migrations.
    * **Containerized Deployment**: Fully containerized with Docker and orchestrated with `docker-compose.yml`.
    * **Production-Ready Proxy**: Includes a Caddy reverse proxy for automatic HTTPS in production.

* **Self-Optimizing Agent & Admin Features:**
    * **AI-Powered Code Modification (`Code Modifier` Plugin)**: Admins can prompt Frankie's "Code Modifier" plugin to analyze, suggest, and (with approval) apply changes to its own backend or frontend codebase.
    * **Automated Code Formatting**: LLM-proposed code changes are automatically formatted using `black` (Python) and `prettier` (frontend files) before admin review.
    * **Automated Testing Integration**: Proposed code changes from the Code Modifier plugin are automatically tested (`pytest` for backend) before admin review.
    * **Human-in-the-Loop Approval Workflow**: All agent-generated code changes, along with explanations, diffs, and test results, are presented to an administrator for explicit review and approval.
    * **Git Versioning**: Approved code changes are automatically committed to the project's Git repository.
    * **Granular File Permissions**: Admins can define a whitelist of files and directories the Code Agent is allowed to access.
    * **Notification System**: Email notifications for agent task status updates (awaiting review, applied, error).
    * **Admin Dashboard**: Centralized UI for user management, agent task monitoring, permissions, notification settings, and genealogy findings review.

* **Extensibility & Advanced Agents:**
    * **Plugin System**: A modular backend architecture allowing new agent capabilities (plugins) and external data source connectors (tools) to be developed and integrated into Frankie.
    * **Odyssey Agent (`Autonomous General Purpose` Plugin)**: An advanced, open-ended agent that, upon receiving a high-level goal, uses an LLM to generate a multi-step plan with milestones. The initial implementation includes this planning phase, with the execution of milestones as the next step for development.
    * **Genealogy Research Agent (`Genealogy Researcher` Plugin)**:
        * Upload and parse GEDCOM family tree files.
        * View basic family tree data (individuals).
        * Initiate AI-driven research tasks for individuals to find missing information.
        * Agent uses "tools" (e.g., a FindAGrave scraper) to query online sources.
        * Presents research findings with source citations, confidence scores, and LLM reasoning for admin review and approval.

## 📂 Project Structure

frankie/
├── .dockerignore
├── .gitignore
├── docker-compose.yml
├── README.md
├── backend/
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── app/
│   │   ├── init.py
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── genealogy_tools/
│   │   ├── plugins/
│   │   └── services/
│   ├── .env.example
│   ├── Dockerfile
│   ├── requirements.txt
│   └── tests/
├── config/
│   └── config.yml
├── frontend/
│   ├── .env
│   ├── Dockerfile
│   ├── index.html
│   ├── nginx.conf
│   ├── package.json
│   ├── public/
│   ├── src/
│   └── vite.config.js
└── proxy/
└── Caddyfile


## 🚀 Getting Started

Follow these steps to get the complete Frankie application, with all its advanced features, up and running.

### Prerequisites

* **Docker**: Ensure Docker Desktop (for Mac/Windows) or Docker Engine (for Linux) is installed and running. [Install Docker](https://docs.docker.com/get-docker/)
* **Docker Compose**: This is usually included with Docker Desktop. For Linux, it might be a separate installation. [Install Docker Compose](https://docs.docker.com/compose/install/)
* **Git**: Required for the self-optimizing agent to commit code changes. [Install Git](https://git-scm.com/downloads)
* **Ollama**: An instance of Ollama must be running and accessible by the Frankie backend container (typically on `http://localhost:11434` if Ollama is on your host machine).
    * Install Ollama from [ollama.com](https://ollama.com/).
    * Pull at least one LLM model that you want Frankie to use, e.g.:
        ```bash
        ollama pull llama3
        ollama pull codellama # Good for code modification tasks
        ```

### 1. Clone the Repository & Initialize Git (If Necessary)

The Frankie project directory **must be a Git repository** for the self-optimizing agent to function.

```bash
# If cloning from a remote repository:
git clone <your-repository-url> frankie
cd frankie

# If you are setting this up from scratch based on these generated files:
mkdir frankie
cd frankie
# << Create all the files and directories as specified in this guide >>
git init
git add .
git commit -m "Initial commit of Frankie project structure and all features"