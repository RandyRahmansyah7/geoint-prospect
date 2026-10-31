"""Storage layer: explicit S3-compatible providers (B2, Filebase) plus an in-memory fake."""

from geoint_prospect.storage.contracts import (
    ObjectRef,
    ProviderConfig,
    ProviderKind,
    PublishResult,
)
from geoint_prospect.storage.keys import (
    InvalidObjectKey,
    manifest_key,
    processed_key,
    raw_key,
    safe_component,
    slug,
    tiles_key,
)
from geoint_prospect.storage.providers import (
    ENV_KEYS,
    FakeProvider,
    S3Provider,
    StorageError,
    StorageProvider,
    build_provider,
    build_providers,
    config_from_env,
    file_checksum,
    parse_providers,
)
from geoint_prospect.storage.publish import publish_file, publish_raw, summarise
from geoint_prospect.storage.smoke import smoke_key, smoke_test

__all__ = [
    "ENV_KEYS",
    "FakeProvider",
    "InvalidObjectKey",
    "ObjectRef",
    "ProviderConfig",
    "ProviderKind",
    "PublishResult",
    "S3Provider",
    "StorageError",
    "StorageProvider",
    "build_provider",
    "build_providers",
    "config_from_env",
    "file_checksum",
    "manifest_key",
    "parse_providers",
    "processed_key",
    "publish_file",
    "publish_raw",
    "raw_key",
    "safe_component",
    "slug",
    "smoke_key",
    "smoke_test",
    "summarise",
    "tiles_key",
]
