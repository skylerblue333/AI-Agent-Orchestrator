# AI-Agent-Orchestrator

![CI](https://github.com/skylerblue333/AI-Agent-Orchestrator/workflows/CI/badge.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.103-00a393.svg)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=flat&logo=redis&logoColor=white)

A highly-scalable, event-driven orchestration layer for managing swarms of autonomous AI agents using FastAPI, Redis Pub/Sub, and OpenTelemetry.

## System Architecture


```mermaid
graph TD
    Client-->|REST/gRPC|API[API Gateway]
    API-->|OpenTelemetry|Tracer[Jaeger/Zipkin]
    API-->|Pub/Sub|Redis[(Redis Event Bus)]
    Redis-->Worker1[AI Worker Node]
    Redis-->Worker2[Data Worker Node]
    Worker1-->LLM[OpenAI/LLM API]
    Worker2-->DB[(PostgreSQL)]
```


## Elite Features
- **Agentic Workflows**: Background task processing simulating LangChain/AutoGPT execution.
- **Observability**: Prometheus metrics endpoint for active agent tracking.
- **Event-Driven**: Asynchronous task dispatch and polling architecture.

## Quick Start
```bash
docker-compose up -d redis
pip install -r requirements.txt
pytest tests/ -v
uvicorn src.main:app --reload
```
