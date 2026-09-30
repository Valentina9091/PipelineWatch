from functools import lru_cache

from .config import get_settings


@lru_cache(maxsize=8)
def _build_store(backend: str, table_name: str | None, region: str, endpoint_url: str | None):
    if backend == "dynamodb":
        if not table_name:
            raise RuntimeError("DYNAMODB_TABLE is required when JOB_STORE=dynamodb")
        from .dynamodb_store import DynamoDBJobStore

        return DynamoDBJobStore(table_name, region, endpoint_url)

    if backend != "sqlite":
        raise RuntimeError(f"Unsupported JOB_STORE: {backend}")

    from .db import SQLiteJobStore

    return SQLiteJobStore()


def get_store():
    settings = get_settings()
    return _build_store(
        settings.job_store,
        settings.dynamodb_table,
        settings.aws_region,
        settings.dynamodb_endpoint_url,
    )


def reset_store_cache() -> None:
    _build_store.cache_clear()
