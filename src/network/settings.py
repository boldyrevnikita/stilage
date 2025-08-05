from typing import Optional, Union

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the application."""
    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore'
    )

    RABBIT_HOST: str
    RABBIT_PORT: Optional[Union[int, str]] = None
    RABBIT_VHOST: Optional[str] = None
    RABBIT_USER: Optional[str] = None
    RABBIT_PASS: Optional[str] = None
    RABBIT_INPUT_QUEUE: str
    RABBIT_OUTPUT_QUEUE: str
    RABBIT_OUTPUT_ROUTING_KEY: str
    RABBIT_HEARTBEAT: int
    S3_ENDPOINT: str
    S3_BUCKET_NAME: str
    S3_DXF_FOLDER_NAME: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    PROCCESS_FUNC: str = 'print'
