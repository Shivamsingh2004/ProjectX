# ProjectX (Dating Platform Aggregator)

Production-ready monorepo for a SaaS platform that aggregates multiple dating
platforms into a single dashboard. The repo includes a Next.js frontend, Spring
Boot microservices, a FastAPI AI service, and data infrastructure.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick Start (Docker)](#quick-start-docker)
- [Local Development](#local-development)
  - [Frontend](#frontend)
  - [Backend Services](#backend-services)
  - [AI Service](#ai-service)
  - [Data Services](#data-services)
- [Configuration](#configuration)
- [Tests & Linting](#tests--linting)
- [Docs](#docs)
- [Deployment](#deployment)

## Overview
ProjectX unifies conversations, profiles, and analytics across multiple dating
platforms. It provides a single inbox, real-time updates, and AI-assisted reply
suggestions to help users manage engagement efficiently.

## Architecture
- **Frontend:** Next.js + TypeScript + Tailwind + Zustand
- **Backend:** Spring Boot microservices + REST + WebSocket
- **AI Service:** FastAPI (OpenAI-compatible NVIDIA endpoint)
- **Data:** PostgreSQL + Redis + Kafka
- **Infra:** Docker Compose + Kubernetes manifests + GitHub Actions CI

## Repository Layout
- `frontend` — Next.js app
- `backend` — Java microservices + API gateway
- `ai-service` — FastAPI AI endpoints
- `database` — schema and seed data
- `docs` — API documentation
- `infra` — Kubernetes manifests

## Prerequisites
- Node.js 22+ and npm
- Java 17 and Maven
- Python 3.12
- Docker + Docker Compose (recommended for running the full stack)

## Quick Start (Docker)
```bash
cp .env.example .env
docker compose up --build
```

Frontend: `http://localhost:3000`  
Gateway: `http://localhost:8080`  
AI service: `http://localhost:8000`

## Local Development

### Frontend
```bash
cd frontend
npm ci
npm run dev
```

Create `frontend/.env.local` (or use your preferred env tooling):
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
NEXT_PUBLIC_SOCKET_URL=http://localhost:8080
NEXT_PUBLIC_SUPABASE_URL=https://<your-project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key_here
```

### Backend Services
```bash
cd backend
mvn clean compile
```

Run individual services:
```bash
mvn -pl api-gateway spring-boot:run
mvn -pl auth-service spring-boot:run
mvn -pl user-service spring-boot:run
mvn -pl messaging-service spring-boot:run
```

### AI Service
```bash
cd ai-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Data Services
Use Docker Compose for PostgreSQL, Redis, and Kafka. The DB schema is mounted
from `database/schema.sql`.

```bash
docker compose up postgres redis kafka
```

## Configuration
Start from `.env.example` and update as needed for Docker Compose:
- `JWT_SECRET`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Optional runtime configuration:
- `SUPABASE_JWKS_URI` and `SUPABASE_ISSUER` for auth-service JWT validation
- `NVIDIA_API_KEY` (required for AI service)
- `NVIDIA_API_BASE` (default: `https://integrate.api.nvidia.com/v1`)
- `NVIDIA_MODEL` (default: `meta/llama-3.1-8b-instruct`)
- `REDIS_HOST`, `REDIS_PORT`, `AI_CACHE_TTL` for AI service caching

## Tests & Linting
- Frontend: `npm run lint`, `npm run build`
- AI service: `python -m py_compile main.py` (no automated test suite yet)
- Backend: `mvn test` (or `mvn clean compile` for a compile-only check)

## Docs
- API: `docs/api.md`
- DB schema: `database/schema.sql`
- K8s manifests: `infra/k8s`

## Deployment
Docker Compose is the fastest path to a full stack. For Kubernetes, see the
manifests in `infra/k8s`.
