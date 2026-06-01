---
title: AI Function Validator
emoji: 🚀
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
---

# 🤖 AI Dataset Validator & Function-Calling Simulator

A system that simulates how LLMs generate function calls and then **validates**, **executes**, and **analyzes** them like a real AI data pipeline — demonstrating JSON handling, function calling, data validation, SQL integration, workflow automation, and AI output debugging.

### 🌐 Live Demo
- **Full Screen App:** [https://arko-hasan-ai-function-validator.hf.space](https://arko-hasan-ai-function-validator.hf.space)
- **Hugging Face Space:** [https://huggingface.co/spaces/arko-hasan/AI-Function-Validator](https://huggingface.co/spaces/arko-hasan/AI-Function-Validator)

---

## ✨ Features

| Feature | Description |
|---|---|
| **🔄 Full Pipeline** | Natural language → Function call generation → Validation → SQL execution → Dataset QA |
| **🛡️ Validator Engine** | Multi-layer validation: JSON, schema, types, SQL safety & injection detection |
| **📋 Function Registry** | Typed schemas with required/optional parameters for 4 registered functions |
| **💾 SQL Execution** | SQLite database with seeded sample data (users, products, orders) |
| **🔍 Dataset QA** | Automated quality checks: nulls, type consistency, outliers, duplicates |
| **💉 Error Injector** | 6 controlled corruption modes to demonstrate validator detection |
| **📊 Analytics Dashboard** | Live charts showing validation rates, error breakdown, function usage |

---

## 🏗️ Architecture

```
Natural Language Input
        │
        ▼
┌─────────────────┐
│  NL → Function  │  (Rule-based mapper simulating LLM output)
│     Mapper      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│   Validator     │────▶│  Analytics   │
│    Engine       │     │    Store     │
└────────┬────────┘     └──────────────┘
         │
         ▼ (if valid)
┌─────────────────┐
│  SQL Execution  │  (SQLite)
│     Layer       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Dataset QA    │  (Nulls, types, outliers, duplicates)
│     Layer       │
└─────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone / navigate to the project
cd ai-function-validator

# Install dependencies
pip install -r requirements.txt

# Start the backend (serves frontend too)
uvicorn backend.main:app --reload --port 8000
```

### Open the Dashboard

Navigate to **http://localhost:8000** in your browser.

---

## 🌍 Free Deployment (Hugging Face Spaces)

This repository is pre-configured for free deployment via **Hugging Face Spaces** using Docker.

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) and create a new Space.
2. Select **Docker** as the SDK and choose **Blank**.
3. Under the Space's Settings, link your GitHub repository (`AbirHasanArko/AI-Function-Validator`) OR drag-and-drop the project files into the **Files** tab.
4. Hugging Face will automatically use the provided `Dockerfile` to build and serve the application entirely for free, with no credit card required.

---

## 📁 Project Structure

```
ai-function-validator/
│
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + API endpoints
│   ├── validator.py          # Multi-layer validation engine
│   ├── function_registry.py  # Function schemas & registry
│   ├── sql_engine.py         # SQLite manager + sample data
│   ├── dataset_checker.py    # Dataset QA analysis
│   ├── error_injector.py     # Controlled error injection
│   ├── nl_to_function.py     # NL → function call mapper
│   └── analytics_store.py    # In-memory analytics tracking
│
├── frontend/
│   ├── index.html            # Dashboard UI
│   ├── styles.css            # Dark theme + glassmorphism
│   └── app.js                # API client + Chart.js analytics
│
├── samples/
│   ├── good_calls.json       # Valid function call examples
│   └── bad_calls.json        # Intentionally broken examples
│
├── requirements.txt
└── README.md
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate` | Generate function call from natural language |
| `POST` | `/api/validate` | Validate a function call JSON |
| `POST` | `/api/execute` | Execute a validated function call |
| `POST` | `/api/analyze` | Execute + run dataset QA |
| `POST` | `/api/pipeline` | Full pipeline in one call |
| `POST` | `/api/inject-error` | Inject controlled errors |
| `GET` | `/api/registry` | View function registry |
| `GET` | `/api/analytics` | Get analytics data |
| `GET` | `/api/injection-modes` | List error injection modes |

Full interactive API docs available at **http://localhost:8000/docs** (Swagger UI).

---

## 🧪 Usage Examples

### Natural Language Pipeline

Enter queries like:
- `"Find users in Dhaka above age 20"`
- `"Show stats for user 5"`
- `"Search products under 1000"`
- `"Order history for user 1, last 5"`

### Error Injection Modes

| Mode | What It Does |
|------|-------------|
| Invalid JSON | Breaks JSON syntax (missing braces, single quotes) |
| Wrong Schema | Removes required fields or adds unknown ones |
| SQL Syntax Error | Introduces typos and invalid operators |
| SQL Injection | Injects `OR 1=1`, `DROP TABLE`, `UNION SELECT` |
| Wrong Types | Changes argument types (string→int, int→string) |
| Unknown Function | Changes to unregistered function name |

---

## 🧱 Tech Stack

- **Backend**: Python, FastAPI, Pydantic
- **Database**: SQLite
- **Validation**: sqlparse, custom JSON/schema validators
- **Frontend**: Vanilla HTML/CSS/JS, Chart.js
- **API Docs**: Swagger UI (auto-generated by FastAPI)

---

## 📊 Analytics Tracked

- ✅ Validation success rate (%)
- ❌ Invalid call rate (%)
- 📈 Error type distribution
- 🔧 Function usage frequency
- 💾 SQL execution failure rate
- ⭐ Average dataset quality score
- 📜 Recent pipeline run history
