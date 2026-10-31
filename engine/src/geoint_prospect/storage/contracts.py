"""Storage contracts: providers, object references, and publish results.

Secrets live in :class:`ProviderConfig.secret_key` (``SecretStr``), so they can never appear in a
manifest, a log line, or a ``model_dump()`` by accident. Object keys and results carry no credentials.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ProviderKind(StrEnum):
    b2 = "b2"
    filebase = "filebase"
    fake = "fake"  # test/Dry validation only; never a production target


class ProviderConfig(BaseModel):
    """Everything needed to talk to one S3-compatible provider."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: ProviderKind
    endpoint: str = Field(min_length=1)
    bucket: str = Field(min_length=1)
    region: str | None = None
    key_id: str = Field(min_length=1)
    secret_key: SecretStr
    path_style: bool = True
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_attempts: int = Field(default=3, ge=1, le=5)


class ObjectRef(BaseModel):
    """A stored object, described without any credential."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: ProviderKind
    bucket: str
    key: str
    bytes: int = Field(ge=0)
    checksum_sha256: str


class PublishResult(BaseModel):
    """Outcome for one object on one provider. Failures are per provider and never hidden."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: ProviderKind
    bucket: str
    key: str
    bytes: int = Field(ge=0)
    checksum_sha256: str
    status: str  # published | verified | skipped | failed | planned
    verified: bool = False
    error: str | None = None
