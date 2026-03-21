# ProjectX - Developer Setup Guide

Welcome to the ProjectX modern dating aggregator platform. This guide will walk you through setting up the enterprise-grade local environment.

## Overview of Services
- **Next.js 15 Frontend**: Running on port `3000`
- **Spring Boot API Gateway**: Running on port `8080` (Entrypoint for all `/api/*` frontend calls)
- **Spring Boot Microservices**: `user-service`, `messaging-service`, `activity-service`, `analytics-service`, `notification-service`
- **FastAPI AI Service**: Port `8000`. Analyzes intent and context.
- **Dependencies**: PostgreSQL (Supabase), Redis, Kafka.

## Prerequisites
- Node.js 20.x+
- Java 17+ (Temurin/Corretto recommended)
- Maven 3.9+
- Python 3.11+
- Docker & Docker Compose (for Postgres, Redis, Kafka)
- A Supabase Project configured with Auth JWKs.

## Local Setup Instructions

### 1. Environment Variables
Create `.env.local` in `frontend/`:
```env
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8080
```

Create `.env` in `ai-service/`:
```env
NVIDIA_API_KEY=your-nvidia-nvapi-key
REDIS_URL=redis://localhost:6379/0
```

### 2. Infrastructure (Docker)
Ensure your backing services are running locally via Docker Compose:
```bash
docker-compose up -d redis kafka
```
*Note: Postgres is managed by Supabase, update `application.yml` files dynamically if running Postgres locally.*

### 3. Start the Backend Microservices
Run the Spring Cloud Gateway and individual services using standard Maven build commands. You can utilize the parallel build:
```bash
cd backend
mvn clean install -DskipTests
```
Then start each service (or run them via your IDE's Run Configuration dashboards):
```bash
java -jar api-gateway/target/api-gateway-0.0.1-SNAPSHOT.jar
# Repeat for user-service, messaging-service, etc.
```

### 4. Start the Python AI Engine
```bash
cd ai-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8000 --reload
```

### 5. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```

Your system is now available at `http://localhost:3000`!

## Debugging & Observability
- All Java logs export directly via OpenTelemetry to local Zipkin/Jaeger if configured.
- See Swagger Docs at `http://localhost:8080/swagger-ui.html`
- AI service produces JSON-structured logs natively containing correlation traces.
