# LinkedIn Post

I built a production-grade Ad Recommendation Engine from scratch — and it's fully running.

Not a tutorial. Not a course project. A real system with a live data pipeline, ML inference, and a working storefront demo.

Here's what's under the hood:

🔁 The Pipeline
User browses the store → JavaScript tracker SDK fires events → FastAPI ingests them → Apache Kafka queues them → Stream Processor consumes, enriches, and persists to PostgreSQL → Recommendation Engine scores and ranks products → Personalised results served back in real time.

🤖 The ML
Hybrid recommendation system combining three strategies:
→ Collaborative Filtering — "users like you also bought this"
→ Content-Based Filtering — "similar to what you've browsed"
→ Popularity Fallback — cold-start handling for new users
Each strategy is weighted and blended into a single ranked score per user.

🛠 The Stack
→ Python 3.11 · FastAPI · asyncpg · Pydantic v2
→ Apache Kafka (Confluent) · Zookeeper
→ PostgreSQL 15 + TimescaleDB · Redis 7
→ TypeScript tracker SDK (runs in the browser)
→ Docker Compose (full local stack in one command)
→ Prometheus · Grafana · Jaeger (full observability)
→ Rate limiting · JWT auth · atomic Lua rate-limit scripts

⚙️ What I'm proud of technically
- Atomic Redis rate limiting using a Lua script — eliminates the race condition in the standard INCR+EXPIRE pattern
- Async cold-start lock on the recommendation engine — prevents thundering-herd reloads under concurrent traffic
- Single ANY($1) query replacing an N+1 loop across similar users in collaborative filtering
- Structured JSON logging with structlog, Prometheus metrics auto-instrumented on every FastAPI route

👀 What it looks like live
The demo storefront fires real browser events, you can watch them land in Kafka UI in real time, and the Recommendations page shows ML match scores per product — all from data the system collected during your own session.

🔗 GitHub: https://github.com/Griffiths-34/Ad-Recommendation-Model

If you're building data-intensive systems, working on recommendation engines, or hiring for backend / ML engineering roles — I'd love to connect.

#DataEngineering #MachineLearning #Python #Kafka #FastAPI #RecommendationSystem #BackendEngineering #MLEngineering #SoftwareEngineering #AdTech
