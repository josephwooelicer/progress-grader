from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str
    jwt_access_expire_seconds: int = 3600        # 1 hour
    jwt_refresh_expire_seconds: int = 28800      # 8 hours

    # Encryption (student API keys at rest)
    encryption_key: str                           # Fernet key, base64-encoded

    # Gitea
    gitea_url: str = "http://gitea:3000"
    gitea_admin_token: str = ""
    gitea_webhook_secret: str = ""
    gitea_bot_username: str = "platform-bot"

    # Minio / object storage
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = ""
    minio_bucket: str = "workspace-archives"
    minio_secure: bool = False

    # Docker
    docker_host: str = "unix:///var/run/docker.sock"

    # Platform
    platform_domain: str = "localhost"
    backend_url: str = "http://backend:8000"
    proxy_url: str = "http://proxy:8001"

    # Resource defaults for workspace containers
    workspace_cpu_quota: int = 100000            # 1 CPU
    workspace_mem_limit: str = "512m"

    @property
    def default_cpu_quota(self) -> int:
        return self.workspace_cpu_quota

    @property
    def default_mem_limit(self) -> str:
        return self.workspace_mem_limit

    @property
    def minio_url(self) -> str:
        scheme = "https" if self.minio_secure else "http"
        return f"{scheme}://{self.minio_endpoint}"


settings = Settings()
