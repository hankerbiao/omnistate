# Getting Started

## Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB

## Installation

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Initialize MongoDB with workflow configurations
python init_mongodb.py

# Initialize RBAC (roles and permissions)
python scripts/init_rbac.py

# Create admin user
python scripts/create_user.py

# Start the backend server
python -m app.main
```

The backend will start on http://localhost:8000

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will start on http://localhost:3000

## Architecture

This is a dual-stack system:

- **Backend**: Configuration-driven workflow/state machine service
- **Frontend**: Server Test Case Designer web application

## Next Steps

- Read the [Backend Architecture](/docs/项目架构规范.md) documentation
- Check the [API Documentation](/docs/后端接口说明.md)