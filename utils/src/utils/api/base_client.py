from typing import ParamSpec, TypeVar

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
    )
