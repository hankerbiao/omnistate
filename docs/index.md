---
layout: home

hero:
  name: "DMLV4"
  text: "Backend Documentation"
  tagline: FastAPI + MongoDB based workflow, test spec, execution and RBAC service
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: Architecture
      link: /architecture

features:
  - title: Workflow
    details: JSON 配置驱动的工作流状态机与业务事项管理
  - title: Test Specs
    details: 测试需求、测试用例、自动化测试用例库管理
  - title: Execution
    details: 平台主导的串行 Case 执行编排与执行历史追踪
  - title: Auth
    details: JWT 认证、RBAC 权限控制和导航访问管理
---

## Quick Start

```bash
cd backend
pip install -r requirements.txt
python app/init_mongodb.py
python scripts/init_rbac.py
python scripts/create_user.py --user-id admin --username 管理员 --password 'admin123' --roles ADMIN
python -m app.main
```

后端默认监听 `http://localhost:8000`。

## Reading Guide

- [开始使用](/guide/getting-started)
- [后端架构说明](/architecture)
- [认证与授权](/guide/authentication)
- [需求与用例管理](/guide/test-requirements-cases)
- [执行编排](/guide/test-execution)
