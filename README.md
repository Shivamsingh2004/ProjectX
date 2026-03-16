# Dating Platform Aggregator

Production-ready starter monorepo for a SaaS platform that aggregates multiple dating platforms into one dashboard.

## Stack
- **Frontend:** Next.js, TypeScript, Tailwind, Zustand, Axios, Framer Motion, Socket.io client
- **Backend:** Java Spring Boot microservices + REST + WebSocket
- **AI Service:** FastAPI
- **Data:** PostgreSQL + Redis + Kafka
- **Infra:** Docker Compose + Kubernetes manifests + GitHub Actions CI

## Services
- `backend/api-gateway`
- `backend/auth-service`
- `backend/user-service`
- `backend/activity-service`
- `backend/messaging-service`
- `backend/analytics-service`
- `backend/notification-service`
- `ai-service`
- `frontend`

## Quick Start
```bash
cp .env.example .env
docker compose up --build
```

Frontend: `http://localhost:3000`
Gateway: `http://localhost:8080`
AI service: `http://localhost:8000`

## Docs
- API: `docs/api.md`
- DB schema: `database/schema.sql`
- K8s manifests: `infra/k8s`
