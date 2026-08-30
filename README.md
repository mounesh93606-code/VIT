# 🚀 SCF Nexus — AI-Powered Supply Chain Finance Platform

> A secure, intelligent and multi-role Supply Chain Finance platform that connects suppliers, buyers and financiers while using AI-driven risk assessment, invoice processing and financial matching.

## 📌 Overview

**SCF Nexus** is a full-stack Supply Chain Finance platform designed to simplify invoice financing and improve access to working capital.

The system connects:

* 🏭 Suppliers
* 🏢 Buyers
* 💰 Financiers
* 👨‍💼 Administrators

The platform combines a modern web interface, FastAPI backend, database management, machine-learning risk models and autonomous AI agents to support the complete financing workflow.

---

## ✨ Key Features

### 🔐 Authentication & Security

* Secure user authentication
* Multi-role access control
* JWT-based authorization
* Protected API endpoints
* CORS configuration
* Security headers and payload-size protection

### 🧾 Invoice Management

* Create and manage invoices
* Track invoice status
* Invoice verification
* Invoice financing workflow
* Settlement tracking

### 🤖 AI-Powered Intelligence

The platform includes multiple AI agents:

* **Invoice Agent** — assists with invoice-related processing
* **Risk Agent** — supports financial risk analysis
* **Matching Agent** — helps match financing requirements
* **Offer Agent** — supports financing offer generation
* **Learning Agent** — provides intelligent learning/decision support

### 📊 Risk Assessment

* ML-based risk modelling
* Risk score generation
* Credit-related analysis
* Financial decision support

### 🤝 Smart Matching

* Supplier-financier matching
* Financing requirement matching
* Automated matching workflows

### 💰 Financing & Offers

* Financing requests
* Financing offers
* Offer management
* Liquidity tracking
* Funding workflow

### 💳 Settlement

* Transaction management
* Settlement processing
* Financing lifecycle tracking

### 📈 Dashboard & Reports

* System statistics
* Supplier directory
* Buyer directory
* Financier directory
* Financial volume tracking
* Funding and settlement analytics
* Administrative reports

---

## 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │     Frontend        │
                    │  HTML / CSS / JS    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     FastAPI         │
                    │      Backend        │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
       ┌───────────┐     ┌───────────┐     ┌───────────┐
       │ Database  │     │ AI Agents │     │ ML Models │
       │ PostgreSQL│     │           │     │ Risk Model│
       └───────────┘     └───────────┘     └───────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Financing Decision  │
                    │ & Smart Matching    │
                    └─────────────────────┘
```

---

## 📂 Project Structure

```text
VIT/
│
├── ai/
│   ├── invoice_agent/
│   ├── learning_agent/
│   ├── matching_agent/
│   ├── offer_agent/
│   └── risk_agent/
│
├── backend/
│   ├── admin/
│   ├── auth/
│   ├── financing/
│   ├── invoices/
│   ├── matching/
│   ├── notifications/
│   ├── offers/
│   ├── reports/
│   ├── risk/
│   ├── security/
│   ├── settlement/
│   ├── verification/
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
│
├── database/
│   ├── connection/
│   ├── models/
│   ├── init_db.py
│   └── schema.sql
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── ml/
│   ├── risk_model/
│   └── training_data/
│
├── tests/
│
├── deployment/
│   └── Docker/
│
├── .env.example
├── .gitignore
├── Dockerfile
├── Procfile
├── docker-compose.yml
├── requirements.txt
└── runtime.txt
```

---

## 🛠️ Technologies Used

| Layer            | Technology             |
| ---------------- | ---------------------- |
| Frontend         | HTML, CSS, JavaScript  |
| Backend          | Python, FastAPI        |
| ORM              | SQLAlchemy             |
| Database         | PostgreSQL / SQLite    |
| AI               | Python-based AI Agents |
| Machine Learning | Python ML models       |
| Authentication   | JWT                    |
| API              | REST API               |
| Deployment       | Docker                 |
| Server           | Uvicorn                |
| Version Control  | Git & GitHub           |

---

## 🔄 Core Workflow

```text
User Registration
       ↓
Authentication
       ↓
Supplier / Buyer / Financier
       ↓
Invoice Creation
       ↓
Invoice Verification
       ↓
AI Risk Assessment
       ↓
Smart Financier Matching
       ↓
Financing Offers
       ↓
Financing Approval
       ↓
Settlement
       ↓
Reports & Analytics
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/mounesh93606-code/VIT.git
cd VIT
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the environment

#### Windows

```bash
venv\Scripts\activate
```

#### Linux / macOS

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Configuration

Create a `.env` file using the provided template:

```bash
cp .env.example .env
```

For Windows:

```bash
copy .env.example .env
```

Update the required environment variables before running the application.

**Do not commit your real `.env` file to GitHub.**

---

## 🗄️ Database

The project supports local SQLite development and PostgreSQL deployment.

### PostgreSQL with Docker

The included Docker Compose configuration provides a PostgreSQL 16 database and connects the web service to it.

```bash
docker compose up --build
```

The database service runs on:

```text
localhost:5432
```

The backend runs on:

```text
localhost:8000
```

---

## ▶️ Run the Backend

From the project root:

```bash
uvicorn backend.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

### API Documentation

FastAPI automatically provides interactive API documentation:

```text
http://localhost:8000/docs
```

---

## ❤️ Health Check

The application provides health endpoints:

```text
GET /health
GET /api/health
```

The health response also reports database connectivity and active AI agents.

---

## 🐳 Docker Deployment

Build and start the complete application using:

```bash
docker compose up --build
```

Stop the containers using:

```bash
docker compose down
```

The repository includes Docker configuration for running the backend and PostgreSQL together.

---

## 🔒 Security

The backend implements several security mechanisms, including:

* JWT authentication
* Role-based access
* CORS configuration
* Payload-size limitation
* Security response headers
* `X-Content-Type-Options`
* `X-Frame-Options`
* Content Security Policy
* Referrer Policy
* HTTPS security configuration

---

## 📊 Main Modules

| Module         | Purpose                         |
| -------------- | ------------------------------- |
| Authentication | User login and authorization    |
| Invoice        | Invoice creation and management |
| Verification   | Invoice verification            |
| Risk           | Risk assessment                 |
| Matching       | Supplier-financier matching     |
| Offers         | Financing offers                |
| Financing      | Funding workflow                |
| Settlement     | Transaction settlement          |
| Notifications  | User notifications              |
| Reports        | Analytics and reports           |
| Admin          | Administrative management       |

---

## 🤖 AI Architecture

The AI layer is divided into specialized agents:

```text
                    AI Layer
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
 Invoice Agent    Risk Agent      Matching Agent
       │               │                │
       └───────────────┼────────────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
        Offer Agent       Learning Agent
```

This modular architecture allows different AI components to focus on specific financial workflows.

---

## 🧪 Testing

Tests are maintained inside the `tests/` directory.

Run the test suite using:

```bash
pytest
```

---

## 🌐 Deployment

The project contains deployment configuration for containerized environments.

Main deployment-related files:

```text
Dockerfile
docker-compose.yml
Procfile
runtime.txt
deployment/Docker/
```

The application can be adapted for cloud platforms such as Render or other Docker-compatible hosting services.

---

## 📸 Screenshots

Add screenshots of your application here:

```markdown
![Dashboard](screenshots/dashboard.png)

![Invoice Management](screenshots/invoices.png)

![Risk Analysis](screenshots/risk-analysis.png)
```

---

## 🚀 Future Enhancements

* 📱 Mobile application
* 🔔 Real-time notifications
* 📊 Advanced financial analytics
* 🧠 More advanced AI risk prediction
* 🔗 Blockchain-based invoice verification
* 💳 Payment gateway integration
* 🌍 Multi-language support
* 📈 Advanced ML-based credit scoring

---

## 🎯 Project Goals

The main goal of SCF Nexus is to make supply chain financing more:

* **Accessible**
* **Intelligent**
* **Secure**
* **Transparent**
* **Automated**
* **Efficient**

---

## 👨‍💻 Author

**Mounesh M**

GitHub:
https://github.com/mounesh93606-code

---

## 📄 License

This project is developed for educational, research and demonstration purposes.
