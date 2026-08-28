import json
from datetime import UTC, datetime
from functools import partial
from typing import Literal, ParamSpec, TypeVar

import patito as pt
import polars as pl
from pydantic_settings import BaseSettings, SettingsConfigDict

# 1. Define modern type aliases that cleanly handle Concatenate
P = ParamSpec("P")
R = TypeVar("R")


class ClientModel(BaseSettings):
    """The settings defined here can be inherrited to create clients that may
    be populated from env variables.

    ```python
    class MockClient(BaseModel):
        type: str = "mock"
        secret: str = Field("default", frozen=True)


    class LiveClient(BaseModel):
        type: str = "live"
        secret: str = Field(validation_alias="live_secret", frozen=True)


    class MyClient(ClientModel):
        client_from_env: MockClient | LiveClient = Field(
            default_factory=dict, discriminator="type"
        )


    os.environ["CLIENT_FROM_ENV__TYPE"] = "mock"
    os.environ["CLIENT_FROM_ENV__LIVE_SECRET"] = "super_secret"
    assert MyClient().secret == "default"

    os.environ["CLIENT_FROM_ENV__TYPE"] = "live"
    assert MyClient().secret == "super_secret"
    ```
    """

    model_config = SettingsConfigDict(
        env_file=".env",  # Reads from a local .env file if present.
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,  # leave all default's alone
        extra="ignore",
    )


class ApiMetadata[I, O](pt.Model):
    """Typically explicitly defined as a means to record the parameters used in the api
    query and the data returned. used with the companion class `AwaitingData` to
    distinguish between models that have data, or models that are missing data.

    >>> class FooParams(pt.Model):
    ...     foo: str
    >>> class BarResponse(pt.Model):
    ...     bar: str
    >>> FooBarData = ApiMetadata[FooParams, BarResponse]
    >>> FooBarParams = AwaitingData[FooParams, BarResponse]
    >>> cfg = FooBarParams(
    ...     service_type="mock",
    ...     api_version="1",
    ...     params=FooParams(foo="input"),
    ... )
    >>> cfg.with_data(BarResponse(bar="output"))

    CAUTION: enum types are not supported pyarrow data types.
    Any literal type annotations are coerced into pyarrow compatible types"""

    service_type: Literal["mock", "live"] = pt.Field(dtype=pl.String)
    api_version: str = pt.Field(dtype=pl.String)
    ingested_at: datetime = pt.Field(default_factory=partial(datetime.now, UTC))
    params: I
    data: O


class AwaitingData[I, O](ApiMetadata[I, None]):
    data: None = None

    def with_data(self, data: bytes) -> "ApiMetadata[I, O]":
        return ApiMetadata[I, O](
            service_type=self.service_type,
            api_version=self.api_version,
            ingested_at=self.ingested_at,
            params=self.params,
            data=json.loads(data),
        )
