import os
from dataclasses import dataclass, field

import chromadb
from dotenv import load_dotenv

from shared import config as cfg


@dataclass
class ChromaClientConfig:
    host: str
    cf_client_id: str
    cf_client_secret: str
    port: int = field(default=cfg.DEFAULT_CHROMA_PORT)
    ssl: bool = field(default=cfg.DEFAULT_CHROMA_SSL)

    @classmethod
    def from_env(cls) -> "ChromaClientConfig":
        """Load Chroma connection settings from environment variables."""
        load_dotenv()
        host = os.getenv(cfg.CHROMA_HOST_KEY)
        client_id = os.getenv(cfg.CF_CLIENT_ID_KEY)
        client_secret = os.getenv(cfg.CF_CLIENT_SECRET_KEY)

        if not host:
            raise EnvironmentError(
                f"Missing required env var: {cfg.CHROMA_HOST_KEY}"
            )
        if not client_id or not client_secret:
            raise EnvironmentError(
                f"Missing Cloudflare Access credentials. "
                f"Expected: {cfg.CF_CLIENT_ID_KEY}, {cfg.CF_CLIENT_SECRET_KEY}"
            )

        return cls(host=host, cf_client_id=client_id, cf_client_secret=client_secret)


class ChromaClientFactory:
    """Builds a Chroma HttpClient with Cloudflare Access headers."""

    @staticmethod
    def create(config: ChromaClientConfig) -> chromadb.HttpClient:
        return chromadb.HttpClient(
            host=config.host,
            port=config.port,
            ssl=config.ssl,
            headers={
                "CF-Access-Client-Id": config.cf_client_id,
                "CF-Access-Client-Secret": config.cf_client_secret,
            },
        )
