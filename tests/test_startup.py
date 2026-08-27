import asyncio
from types import SimpleNamespace

from app.api.routes import health_check
from app.main import app


def test_health_check_loads_supplied_data() -> None:
    async def start_application() -> dict[str, int | str]:
        async with app.router.lifespan_context(app):
            return health_check(SimpleNamespace(app=app)).model_dump()

    # Avoid an HTTP test-client dependency while still checking app startup and
    # the health route's response contract.
    assert asyncio.run(start_application()) == {
        "status": "ok",
        "tickets": 500,
        "accounts": 50,
        "knowledge_base_documents": 9,
    }
