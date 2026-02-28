# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Server Test Case Designer** - A React + TypeScript + Vite web application for managing test requirements and test cases for server hardware validation (DDR5 memory testing, server validation, etc.). Integrates with a local AI service for AI-assisted features.

## Quick Start

```bash
npm install              # Install dependencies
npm run dev              # Start dev server (port 3000)
```

Then open http://localhost:3000

## Commands

```bash
# Development
npm run dev              # Dev server (port 3000, with HMR)

# Building
npm run build            # Production build to dist/
npm run preview          # Preview production build locally

# Code Quality
npm run lint             # Type check (tsc --noEmit)

# Cleanup
npm run clean            # Remove dist/ folder
```

## Environment Configuration

Create `.env.local`:
```bash
APP_URL=http://localhost:3000          # Application URL (auto-injected in AI Studio)
GEMINI_API_KEY=your_key_here           # Optional: Gemini API key for AI features
```

## Tech Stack

- **React 19** - Modern React with hooks
- **TypeScript 5.8** - Type safety
- **Vite 6** - Fast build tool and dev server
- **TailwindCSS 4** - Utility-first CSS framework
- **@tailwindcss/vite** - Vite integration
- **@vitejs/plugin-react** - React support for Vite
- **Lucide React** - Icon library
- **Motion (framer-motion)** - Animations
- **Local AI Service** - OpenAI-compatible API for AI-assisted features

## Application Architecture

### Key Files
- **`src/App.tsx`** - Main application component with all views and centralized state management
- **`src/types.ts`** - TypeScript interfaces/enums (TestRequirement, TestCase, User, Role, etc.)
- **`src/main.tsx`** - React entry point
- **`src/index.css`** - Global styles (TailwindCSS imports)
- **`vite.config.ts`** - Vite configuration with TailwindCSS and React plugins

### Single-File Component Architecture

The app uses a **single-file architecture** where all UI is in `App.tsx` with view state management via `currentView` state:

**Available Views**:
- `req_list` - Test requirement list with filtering/search
- `req_form` - Create/edit test requirement (form validation)
- `req_detail` - View requirement details with linked test cases
- `case_form` - Create new test case with AI-assisted step generation
- `user_mgmt` - User and role management (RBAC interface)

### Data Models (`src/types.ts`)

**Core Entities**:
- **`TestRequirement`** - Test requirements with technical specs, priority, status
- **`TestCase`** - Test cases with steps, attachments, approval history
- **`User`** / **`Role`** - User management with role-based permissions

**Key Enums**:
- `TestCaseStatus`, `Priority`, `RiskLevel`, `VisibilityScope`, `TestCaseCategory`, `Confidentiality`

### AI Integration

The app integrates with a **local AI service** for AI-assisted features:

- **Endpoint**: `http://172.17.167.43:8000/v1` (OpenAI-compatible)
- **Model**: `/models/coder/minimax/MiniMax-M2`
- **Function**: `callLocalAI()` in `App.tsx`

**AI Features**:
- Text polishing (improve requirement/case descriptions)
- Test step generation (AI-assisted test case creation)
- Content optimization

### State Management

All state is managed in `App.tsx` using React hooks:
- `currentView` - Controls which view is displayed
- `requirements` / `testCases` - Data state
- `currentUser` - Authentication state
- `selectedRequirement` / `selectedTestCase` - Selection state

No external state management library (Redux, Zustand) - keeping it simple with React built-in state.

### Styling & UI

- **TailwindCSS 4** - Utility-first styling
- **Lucide React** - Modern icon library (PenTool, Plus, Search, etc.)
- **Motion** - Smooth animations for view transitions
- **Responsive design** - Mobile-friendly layout
- **Dark/light mode** - System preference detection