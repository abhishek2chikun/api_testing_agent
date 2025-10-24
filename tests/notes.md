# Notes & next steps

## Architecture

The project is organized into clear functional modules:
- **core/**: Webhook endpoints and main orchestration pipeline
- **integrations/**: External service clients (Jira, GitHub)
- **services/**: Business logic for test generation and execution
- **config/**: Configuration and environment management
- **examples/**: Sample test templates

## Production Considerations

- Use a task queue (Celery or RQ) for async processing instead of FastAPI BackgroundTasks
- Secure webhook signatures to validate incoming requests
- Run generated code in isolated sandboxed runners (Docker/Kubernetes)
- Add observability: logging, metrics, tracing
- Implement rate limiting and error retry logic
- Use secrets manager for credentials (AWS Secrets Manager, HashiCorp Vault)

## Switching to Java Tests

To generate Java/Rest-Assured tests instead of pytest:
1. In `core/orchestrator.py`, change `language='python'` to `language='java'`
2. Call `run_maven_tests_in_docker` instead of `run_pytests_in_docker`

The LLM will automatically use JAVA_PROMPT_TEMPLATE from `services/test_generator/prompts.py`.


