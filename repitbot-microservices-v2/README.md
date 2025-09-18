# RepitBot Microservices (Next-Gen)

Complete re-imagining of RepitBot as a microservices platform for tutors, students, and parents.

## Services

- **Auth Service (8000)** – credentials, JWT tokens, role management
- **User Service (8001)** – user directory, access codes, Telegram identities
- **Lesson Service (8002)** – scheduling and tracking of lessons
- **Homework Service (8003)** – assignments, submissions, reviews
- **Payment Service (8004)** – payments, invoices, balances
- **Notification Service (8005)** – delivery preferences and dispatch log
- **API Gateway (8080)** – single entry point and request routing
- **Telegram Bot** – Python Telegram Bot v21 client integrated through the gateway
- **Infrastructure** – PostgreSQL (per-service DBs), Redis cache, RabbitMQ event bus

## Quick Start

```bash
cd repitbot-microservices-v2
cp .env.example .env
for service in services/* api-gateway telegram-bot; do cp "$service/.env.example" "$service/.env"; done
# Edit telegram-bot/.env and .env if you need to override secrets (token already pre-filled for local test)
docker-compose up --build
```

After the stack bootstraps:
- Swagger UI for every service lives at `http://localhost:<service_port>/api/v1/<resource>/docs`
- API Gateway documentation is at `http://localhost:8080/docs`
- RabbitMQ management console is at `http://localhost:15672` (repitbot/repitbot)
- Telegram bot connects in polling mode once the gateway is ready

## Database & Migrations

Each service owns a dedicated PostgreSQL database (`repitbot_auth`, `repitbot_user`, ...). Databases are created by `infrastructure/postgres/init-databases.sql` during container start.

Migrations are managed with Alembic and executed automatically on service startup. You can run them manually as well:

```bash
# Example: run migrations for user-service
docker-compose run --rm user-service alembic upgrade head
```

## Event Bus

`repitbot_shared` now ships with an `EventBus` implementation backed by RabbitMQ (aio-pika). Any service can publish/subscribe to domain events via:

```python
from repitbot_shared.events import Event, EventBus, EventType
```

A RabbitMQ container (with management UI) is included in `docker-compose.yml` and pre-configured through `.env` files.

## Repository Structure

```
services/
  auth-service/             # FastAPI app + Alembic migrations
  user-service/
  lesson-service/
  homework-service/
  payment-service/
  notification-service/
api-gateway/                # Proxy to all services
telegram-bot/               # python-telegram-bot 21+, works via the gateway
shared/python/repitbot_shared
                            # shared config/logging/db/event bus helpers
infrastructure/postgres/    # database bootstrap scripts
scripts/                    # reserved for future ops tooling
```

## Next Steps

1. Harden JWT secret & service credentials for non-local deployments.
2. Extend services to emit/consume RabbitMQ events for workflows (payments, notifications, etc.).
3. Grow the Telegram bot feature set (payments overview, notifications toggle, analytics).
4. Add contract & e2e tests (per-service test suites already scaffolded).
5. Wire CI/CD: container builds, migrations, staged rollouts.
