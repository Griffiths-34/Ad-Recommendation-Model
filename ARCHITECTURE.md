# 🎯 Ad Recommendation Platform - Architecture Diagrams

## 1. High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                  │
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │
│  │   Browser    │    │    Mobile    │    │   Desktop    │            │
│  │              │    │     App      │    │     App      │            │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘            │
│         │                   │                   │                     │
│         └───────────────────┴───────────────────┘                     │
│                             │                                          │
│                    ┌────────▼─────────┐                                │
│                    │  Tracker SDK JS  │                                │
│                    │  - Event batching │                               │
│                    │  - Retry logic   │                                │
│                    │  - Privacy       │                                │
│                    └────────┬─────────┘                                │
└─────────────────────────────┼──────────────────────────────────────────┘
                              │ HTTPS
                              ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY LAYER                               │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    Load Balancer (NGINX)                         │ │
│  │  - SSL termination  - Rate limiting  - CORS  - Compression      │ │
│  └────────────────────────────┬─────────────────────────────────────┘ │
└────────────────────────────────┼──────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      MICROSERVICES LAYER                               │
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │
│  │ Event Collector │  │ Recommendation  │  │   Ad Server     │       │
│  │   (FastAPI)     │  │    Engine       │  │   (FastAPI)     │       │
│  │                 │  │  (FastAPI/ML)   │  │                 │       │
│  │ - Validation    │  │ - Collab Filter │  │ - Ad Selection  │       │
│  │ - Enrichment    │  │ - Content Based │  │ - Tracking      │       │
│  │ - Publishing    │  │ - Deep Learning │  │ - Budgets       │       │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘       │
│           │                    │                    │                 │
│           │    ┌───────────────┴────────────────┐   │                 │
│           │    │                                 │   │                 │
│  ┌────────▼────▼──────┐              ┌──────────▼───▼─────────┐       │
│  │  Stream Processor  │              │   Bidding Engine       │       │
│  │   (Flink/Python)   │              │        (Go)            │       │
│  │                    │              │                        │       │
│  │ - Aggregations     │              │ - RTB Logic            │       │
│  │ - Features         │              │ - Auctions             │       │
│  │ - Profiles         │              │ - Sub-50ms response    │       │
│  └────────┬───────────┘              └────────────────────────┘       │
└───────────┼──────────────────────────────────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       MESSAGE QUEUE LAYER                              │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                      Apache Kafka                                │ │
│  │                                                                  │ │
│  │  Topics:                                                         │ │
│  │  ├─ user-events        (main event stream)                      │ │
│  │  ├─ user-events-dlq    (dead letter queue)                      │ │
│  │  ├─ user-profiles      (profile updates)                        │ │
│  │  ├─ recommendations    (recommendation results)                 │ │
│  │  ├─ ad-impressions     (ad tracking)                            │ │
│  │  └─ ad-clicks          (click tracking)                         │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                      │
│                                                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐             │
│  │  PostgreSQL   │  │     Redis     │  │     MinIO     │             │
│  │  + TimescaleDB│  │               │  │   (S3-like)   │             │
│  │               │  │               │  │               │             │
│  │ Events        │  │ Cache         │  │ Raw Data      │             │
│  │ Users         │  │ Sessions      │  │ Backups       │             │
│  │ Ads           │  │ Features      │  │ Models        │             │
│  │ Campaigns     │  │ Rate Limits   │  │ Archives      │             │
│  └───────────────┘  └───────────────┘  └───────────────┘             │
└────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   OBSERVABILITY LAYER                                   │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │  Prometheus  │→│   Grafana    │  │    Jaeger    │                │
│  │  (Metrics)   │  │ (Dashboard)  │  │  (Tracing)   │                │
│  └──────────────┘  └──────────────┘  └──────────────┘                │
│                                                                         │
│  ┌────────────────────────────────────────────────────┐                │
│  │          Elasticsearch + Kibana (Logs)            │                │
│  └────────────────────────────────────────────────────┘                │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow Diagram

```
USER ACTION
    │
    ▼
┌───────────────────────────────────────┐
│  1. User clicks "Add to Cart"        │
│     on e-commerce site                │
└───────────┬───────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│  2. Tracker SDK captures event:       │
│     {                                 │
│       eventName: "add_to_cart",       │
│       productId: "prod-001",          │
│       price: 99.99,                   │
│       timestamp: 1700000000000        │
│     }                                 │
└───────────┬───────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│  3. SDK batches event (5 events)      │
│     Sends via HTTP POST               │
└───────────┬───────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│  4. Event Collector API               │
│     - Validates event                 │
│     - Enriches with IP, User-Agent    │
│     - Checks rate limit               │
│     - Returns 201 Created             │
└───────────┬───────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│  5. Publishes to Kafka                │
│     Topic: "user-events"              │
│     Key: user_id or session_id        │
└───────────┬───────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│  6. Stream Processor consumes         │
│     - Updates user profile            │
│     - Calculates features             │
│     - Writes to PostgreSQL            │
│     - Updates Redis cache             │
└───────────┬───────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│  7. ML Model training (batch)         │
│     - Collaborative filtering         │
│     - Content-based filtering         │
│     - Updates model registry          │
└───────────┬───────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│  8. User visits news site             │
│     Ad slot triggers RTB auction      │
└───────────┬───────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│  9. Bidding Engine                    │
│     - Queries Recommendation Engine   │
│     - Calculates bid price            │
│     - Submits bid                     │
└───────────┬───────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│ 10. Wins auction                      │
│     Ad Server delivers ad             │
│     Tracks impression                 │
└───────────┬───────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│ 11. User sees personalized ad         │
│     for product they viewed           │
└───────────────────────────────────────┘
```

---

## 3. Recommendation Engine Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    RECOMMENDATION ENGINE                       │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                   Feature Store (Redis)                  │ │
│  │  - User vectors                                          │ │
│  │  - Product vectors                                       │ │
│  │  - User history                                          │ │
│  │  - Real-time features                                    │ │
│  └────────────┬─────────────────────────────────────────────┘ │
│               │                                               │
│               ▼                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Model Serving Layer                         │ │
│  │                                                           │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────┐ │ │
│  │  │ Collaborative  │  │  Content-Based │  │   Hybrid   │ │ │
│  │  │   Filtering    │  │    Filtering   │  │   Model    │ │ │
│  │  │                │  │                │  │            │ │ │
│  │  │ - Matrix       │  │ - TF-IDF       │  │ - Ensemble │ │ │
│  │  │   Factorization│  │ - Embeddings   │  │ - Weighted │ │ │
│  │  │ - User-User    │  │ - Categories   │  │   Average  │ │ │
│  │  │ - Item-Item    │  │ - Metadata     │  │            │ │ │
│  │  └────────┬───────┘  └────────┬───────┘  └─────┬──────┘ │ │
│  │           │                   │                 │        │ │
│  │           └───────────────────┴─────────────────┘        │ │
│  │                              │                            │ │
│  │                              ▼                            │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │              Ranking & Filtering                   │  │ │
│  │  │  - Business rules                                  │  │ │
│  │  │  - Diversity                                       │  │ │
│  │  │  - Freshness                                       │  │ │
│  │  │  - Personalization                                 │  │ │
│  │  └──────────────────────┬─────────────────────────────┘  │ │
│  │                         │                                 │ │
│  │                         ▼                                 │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │              A/B Testing Framework                 │  │ │
│  │  │  - Experiment management                           │  │ │
│  │  │  - Traffic splitting                               │  │ │
│  │  │  - Metrics tracking                                │  │ │
│  │  └──────────────────────┬─────────────────────────────┘  │ │
│  └─────────────────────────┼──────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  API Response                          │ │
│  │  {                                                     │ │
│  │    "recommendations": [                               │ │
│  │      {"productId": "prod-001", "score": 0.95},        │ │
│  │      {"productId": "prod-042", "score": 0.87}         │ │
│  │    ]                                                   │ │
│  │  }                                                     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Monitoring & Observability

```
┌────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Event   │  │  Recom   │  │   Ad     │  │ Bidding  │      │
│  │Collector │  │  Engine  │  │  Server  │  │  Engine  │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │             │             │             │             │
│       └─────────────┴─────────────┴─────────────┘             │
│                          │                                     │
└──────────────────────────┼─────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   METRICS     │  │     LOGS      │  │    TRACES     │
│  (Prometheus) │  │    (ELK)      │  │   (Jaeger)    │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        │                  │                  │
        ▼                  ▼                  ▼
┌────────────────────────────────────────────────────────┐
│              VISUALIZATION LAYER                       │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │                  Grafana                        │  │
│  │                                                  │  │
│  │  Dashboard 1: System Health                     │  │
│  │  ├─ CPU/Memory usage                            │  │
│  │  ├─ Request rates                               │  │
│  │  └─ Error rates                                 │  │
│  │                                                  │  │
│  │  Dashboard 2: Business Metrics                  │  │
│  │  ├─ Events per second                           │  │
│  │  ├─ Recommendations served                      │  │
│  │  ├─ Ad impressions                              │  │
│  │  ├─ Click-through rate                          │  │
│  │  └─ Revenue                                     │  │
│  │                                                  │  │
│  │  Dashboard 3: ML Performance                    │  │
│  │  ├─ Model accuracy                              │  │
│  │  ├─ Inference latency                           │  │
│  │  └─ Model version                               │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │                  Kibana                         │  │
│  │  - Log search and analysis                      │  │
│  │  - Error tracking                               │  │
│  │  - Audit trails                                 │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                  ALERTING LAYER                        │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │              Alert Manager                      │  │
│  │                                                  │  │
│  │  Rules:                                         │  │
│  │  ├─ High error rate (> 1%)                     │  │
│  │  ├─ High latency (P99 > 100ms)                 │  │
│  │  ├─ Service down                                │  │
│  │  ├─ Kafka lag (> 1000 messages)                │  │
│  │  └─ Database connection errors                 │  │
│  │                                                  │  │
│  │  Notifications:                                 │  │
│  │  ├─ Slack                                       │  │
│  │  ├─ Email                                       │  │
│  │  ├─ PagerDuty                                   │  │
│  │  └─ SMS (critical only)                        │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Deployment Architecture (Kubernetes)

```
┌────────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                          │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                      Ingress Controller                  │ │
│  │  - SSL termination                                       │ │
│  │  - Load balancing                                        │ │
│  │  - Rate limiting                                         │ │
│  └──────────────────┬───────────────────────────────────────┘ │
│                     │                                         │
│         ┌───────────┴───────────┬─────────────┐              │
│         ▼                       ▼             ▼              │
│  ┌─────────────┐      ┌─────────────┐  ┌─────────────┐      │
│  │  Namespace  │      │  Namespace  │  │  Namespace  │      │
│  │   (prod)    │      │   (staging) │  │    (dev)    │      │
│  │             │      │             │  │             │      │
│  │ ┌─────────┐ │      │             │  │             │      │
│  │ │ Event   │ │      │             │  │             │      │
│  │ │Collector│ │      │             │  │             │      │
│  │ │         │ │      │             │  │             │      │
│  │ │ Pods: 3 │ │      │             │  │             │      │
│  │ │ CPU: 2  │ │      │             │  │             │      │
│  │ │ Mem: 2GB│ │      │             │  │             │      │
│  │ └─────────┘ │      │             │  │             │      │
│  │             │      │             │  │             │      │
│  │ ┌─────────┐ │      │             │  │             │      │
│  │ │  Recom  │ │      │             │  │             │      │
│  │ │ Engine  │ │      │             │  │             │      │
│  │ │         │ │      │             │  │             │      │
│  │ │ Pods: 5 │ │      │             │  │             │      │
│  │ │ CPU: 4  │ │      │             │  │             │      │
│  │ │ Mem: 4GB│ │      │             │  │             │      │
│  │ └─────────┘ │      │             │  │             │      │
│  │             │      │             │  │             │      │
│  │ ┌─────────┐ │      │             │  │             │      │
│  │ │   Ad    │ │      │             │  │             │      │
│  │ │ Server  │ │      │             │  │             │      │
│  │ │         │ │      │             │  │             │      │
│  │ │ Pods: 3 │ │      │             │  │             │      │
│  │ │ CPU: 2  │ │      │             │  │             │      │
│  │ │ Mem: 2GB│ │      │             │  │             │      │
│  │ └─────────┘ │      │             │  │             │      │
│  └─────────────┘      └─────────────┘  └─────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │              StatefulSets (Databases)                    ││
│  │                                                           ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              ││
│  │  │PostgreSQL│  │  Redis   │  │  Kafka   │              ││
│  │  │          │  │          │  │          │              ││
│  │  │ Pods: 3  │  │ Pods: 3  │  │ Pods: 3  │              ││
│  │  │ (HA)     │  │ (Cluster)│  │ (Cluster)│              ││
│  │  └──────────┘  └──────────┘  └──────────┘              ││
│  └──────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │              Auto-scaling Policies                       ││
│  │                                                           ││
│  │  - HPA (Horizontal Pod Autoscaler)                       ││
│  │    Target CPU: 70%                                       ││
│  │    Min replicas: 2                                       ││
│  │    Max replicas: 20                                      ││
│  │                                                           ││
│  │  - VPA (Vertical Pod Autoscaler)                         ││
│  │    Automatic resource adjustment                         ││
│  └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Security Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                          │
│                                                                 │
│  Layer 1: Network Security                                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  - WAF (Web Application Firewall)                       │  │
│  │  - DDoS protection                                       │  │
│  │  - IP whitelisting                                       │  │
│  │  - VPC isolation                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│                              ▼                                 │
│  Layer 2: API Security                                         │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  - API Gateway                                           │  │
│  │  - Rate limiting (per IP, per user)                     │  │
│  │  - JWT authentication                                    │  │
│  │  - API key validation                                    │  │
│  │  - Input validation                                      │  │
│  │  - CORS policies                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│                              ▼                                 │
│  Layer 3: Application Security                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  - Role-based access control (RBAC)                     │  │
│  │  - Data encryption at rest                              │  │
│  │  - Data encryption in transit (TLS 1.3)                 │  │
│  │  - Secret management (Vault/AWS Secrets Manager)        │  │
│  │  - SQL injection prevention                             │  │
│  │  - XSS protection                                        │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│                              ▼                                 │
│  Layer 4: Data Security                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  - PII anonymization                                     │  │
│  │  - GDPR compliance                                       │  │
│  │  - Data retention policies                              │  │
│  │  - Right to deletion                                     │  │
│  │  - Audit logging                                         │  │
│  │  - Database encryption                                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│                              ▼                                 │
│  Layer 5: Infrastructure Security                              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  - Container scanning                                    │  │
│  │  - Vulnerability scanning                                │  │
│  │  - Security updates                                      │  │
│  │  - Access logging                                        │  │
│  │  - Intrusion detection                                   │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Legend

```
Symbols Used:
│  - Connection/Flow
▼  - Data flow direction
┌┐ - Container/Service boundary
└┘ - Container/Service boundary
→  - Direct connection
├─ - Tree branch
```

**These diagrams represent a production-ready, enterprise-grade system! 🚀**
