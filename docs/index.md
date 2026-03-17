---
layout: home

hero:
  name: "DMLV4"
  text: "Server Test Case Designer"
  tagline: A dual-stack system for workflow management and test case design
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started

features:
  - title: Backend
    details: FastAPI + Beanie ODM + MongoDB configuration-driven workflow service
  - title: Frontend
    details: React + TypeScript + Vite web application for test case management
  - title: Workflow
    details: JSON-configured state machine for business item lifecycles
---

## Quick Start

### Backend Setup

```bash
cd backend
python init_mongodb.py
python scripts/init_rbac.py
python -m app.main
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```