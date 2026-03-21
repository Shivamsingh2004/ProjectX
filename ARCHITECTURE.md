# ProjectX Engineering Architecture

```mermaid
graph TD
    %% Frontend & CDN
    subgraph Edge
        CDN[Vercel Edge CDN]
        UI[Next.js + Zustand + Tailwind]
        CDN --> UI
    end

    %% External Systems
    subgraph External Platforms
        SUPA[Supabase Auth / Postgres]
        NV[NVIDIA AI API]
    end

    UI -- "Authentication (JWT)" --> SUPA

    %% API Gateway Layer
    subgraph API Gateway
        GW[Spring Cloud Gateway MVC]
        UI -- "/api/* (Bearer Token)" --> GW
    end

    %% Microservices Layer
    subgraph Spring Boot Microservices
        USER[user-service (Port 8082)]
        MSG[messaging-service (Port 8084)]
        ACT[activity-service (Port 8083)]
        ANL[analytics-service (Port 8085)]
        NOTF[notification-service (Port 8086)]
        
        GW -->|/api/users| USER
        GW -->|/api/messages| MSG
        GW -->|/api/activity| ACT
        GW -->|/api/analytics| ANL
        GW -->|/api/notifications| NOTF
    end

    %% Event Bus
    subgraph Event Broker
        KAFKA[Apache Kafka]
        ACT -- Publish --> KAFKA
        ANL -- Subscribe --> KAFKA
        NOTF -- Subscribe --> KAFKA
    end

    %% AI Service
    subgraph AI Python Service
        FAST[FastAPI Server]
        REDIS[Redis Cache]
        MSG -- "Request Reply (CircuitBreaker)" --> FAST
        FAST -- Cache/Fetch --> REDIS
        FAST -- Prompting --> NV
    end

    %% Databases
    USER -- "User profiles, Match data" --> SUPA
    MSG -- "Conversations, history" --> SUPA
    NOTF -- "Push configurations" --> SUPA
```

## System Resilience & Scalability Characteristics
- **Observability**: Standardized `micrometer-tracing-bridge-otel` and Zipkin telemetry.
- **Circuit Breakers**: External dependencies (e.g. NVIDIA API in Python, and Python caller in Java) are wrapped by `Resilience4j`.
- **Global Responses**: All JSON payloads intercepted by `@RestControllerAdvice` implementing a strict `{ success, data, error, meta }` syntax.
- **Cache Layers**: Python dictates heavy Prompt caching into Redis (TTL expiry and invalidation).
- **Asynchronous Flow**: Traffic metrics and heavy push notifications shift off the web request thread onto Apache Kafka consumers.
