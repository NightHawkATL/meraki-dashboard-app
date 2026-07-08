# Meraki Dashboard App

A robust, full-stack web application designed to streamline and automate Cisco Meraki network operations. This platform provides a secure, role-based user interface to execute dynamic Python automation scripts against specific Meraki organizations and networks.

## 🚀 Overview

The Meraki Dashboard App bridges the gap between Python automation and a user-friendly web interface. Instead of running Meraki API scripts via the command line, users can log into a secure portal, select a script, choose their target Organization and Network, and watch real-time execution progress.

### 🌟 Key Features (In Development)
* **Dynamic Script Execution:** Automatically loads Python automation scripts from a connected GitHub repository.
* **Smart Search & Auto-Fill:** Quickly search for network names or site codes to auto-populate script execution targets.
* **Real-Time Progress:** Live progress bars and terminal logs streamed via WebSockets during script execution.
* **Secure API Management:** Meraki API keys are AES-encrypted at rest (using Fernet) and only decrypted in memory during script execution.
* **Site Integrations:** Pulls and displays live hotel address/contact info (Google Places API) and maps (Mapbox) based on the selected network.
* **Enterprise Security:** Built-in Role-Based Access Control (RBAC) and Mandatory Two-Factor Authentication (2FA/TOTP).
* **Job History & Output:** Automatically generates and stores output `.xlsx` or `.txt` files for easy download after a script finishes.

## 🛠️ Tech Stack

**Frontend:**
* [React 18](https://react.dev/) (via Vite)
* [Material-UI (MUI)](https://mui.com/) for UI components and Dark/Light theming
* [TanStack Query](https://tanstack.com/query/latest) for API data caching

**Backend:**
* [FastAPI](https://fastapi.tiangolo.com/) (Python) for high-performance REST APIs and WebSockets
* [Celery](https://docs.celeryq.dev/) + [Redis](https://redis.io/) for asynchronous background task queuing
* [Cisco Meraki Python SDK](https://developer.cisco.com/meraki/api-v1/python/) (Handles automatic 429 rate-limit retries)

**Database & Infrastructure:**
* [PostgreSQL 15](https://www.postgresql.org/) for robust relational data storage
* [Docker & Docker Compose](https://www.docker.com/) for single-command deployment

## 📂 Project Structure

```text
meraki-dashboard-app/
├── frontend/             # React application (Vite + MUI)
├── backend/              # FastAPI server and Celery background workers
│   ├── app/              # API routes, database models, and security logic
│   └── scripts/          # Local clone directory for GitHub Python scripts
├── .env                  # Environment variables (Ignored in Git)
├── docker-compose.yml    # Orchestrates the database, backend, frontend, and redis
└── README.md
```

## ⚙️ Getting Started

### Prerequisites
* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/install/)
* Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/NightHawkATL/meraki-dashboard-app.git
   cd meraki-dashboard-app
   ```

2. **Run the Docker Stack:**
   This command will build the React frontend, set up the Python backend, initialize the PostgreSQL database, and spin up the Redis cache.
   ```bash
   docker-compose up -d --build
   ```

3. **Access the Application:**
   * **Frontend UI:** Open `http://localhost:3000` in your browser.
   * **Backend API (FastAPI Docs):** Open `http://localhost:8000/docs` to see the automated Swagger API documentation.

### Stopping the Application
To stop the application and background workers without losing your database data:
```bash
docker-compose down
```

## 🔒 Environment Variables
*Note: A `.env` file should be created in the root directory for production deployments.*

| Variable | Description |
|----------|-------------|
| `DB_USER` | PostgreSQL Username |
| `DB_PASSWORD` | PostgreSQL Password |
| `DB_NAME` | PostgreSQL Database Name |
| `SECRET_KEY` | JWT Secret Key for User Sessions |
| `ENCRYPTION_KEY` | Master Fernet key for encrypting Meraki API keys |

---
*Developed for seamless Meraki Network Management.*