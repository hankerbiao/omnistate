# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A minimal React 19 + TypeScript + Vite frontend application for a test case management platform. It provides authentication and manages test cases and execution agents.

## Tech Stack

- **Frontend**: React 19 + TypeScript + Vite 8
- **Styling**: Plain CSS (App.css, index.css)
- **Build**: TypeScript compilation + Vite
- **Linting**: ESLint 9

## Commands

```bash
npm install              # Install dependencies
npm run dev              # Start dev server (port 5173)
npm run build            # Production build
npm run lint             # Run ESLint
npm run preview          # Preview production build
```

## Architecture

The app is a single-page React application with view state management:

**Main Components** (`src/components/`):
- `LoginPage.tsx` - JWT authentication
- `TestCaseList.tsx` - Test case management view
- `AgentList.tsx` - Execution agent management view

**API Layer** (`src/services/api.ts`):
- Uses fetch API with JWT Bearer token authentication
- Base URL configured via `VITE_API_BASE_URL` env var (default: `http://localhost:8000/api/v1`)
- Token stored in localStorage under `jwt_token`

**Routing** (`src/App.tsx`):
- Simple state-based routing: `currentPage` state switches between `'testCases'` and `'agents'`
- Login state managed via localStorage JWT token check on mount

## Configuration

Environment variables (`.env`):
```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```