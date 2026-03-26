"""Docker-based workspace lifecycle management."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import docker
import jwt
from docker.errors import NotFound
from docker.models.containers import Container

from app.config import settings
from app.models.workspace import Workspace


def _workspace_token(student_id: uuid.UUID, project_id: uuid.UUID, workspace_id: uuid.UUID) -> str:
    """Generate a long-lived JWT scoped to this workspace for the VS Code extension."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(student_id),
        "role": "student",
        "workspace_id": str(workspace_id),
        "project_id": str(project_id),
        "iat": now,
        # Extension token valid for 90 days — refreshed on workspace re-provision
        "exp": now + timedelta(days=90),
        "type": "workspace",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

_WORKSPACE_IMAGE = "progress-grader/workspace:latest"
_NETWORK = "progress-grader"


def _client() -> docker.DockerClient:
    return docker.from_env() if settings.docker_host == "unix:///var/run/docker.sock" \
        else docker.DockerClient(base_url=settings.docker_host)


def _traefik_labels(subdomain: str) -> dict[str, str]:
    host = f"{subdomain}.{settings.platform_domain}"
    return {
        "traefik.enable": "true",
        f"traefik.http.routers.{subdomain}.rule": f"Host(`{host}`)",
        f"traefik.http.routers.{subdomain}.middlewares": "forward-auth@file",
        f"traefik.http.services.{subdomain}.loadbalancer.server.port": "3000",
    }


def _resource_kwargs(project_resource_overrides: dict | None) -> dict[str, Any]:
    overrides = project_resource_overrides or {}
    return {
        "cpu_quota": overrides.get("cpu_quota", settings.default_cpu_quota),
        "mem_limit": overrides.get("mem_limit", settings.default_mem_limit),
    }


def create_container(workspace: Workspace, resource_overrides: dict | None) -> tuple[str, str]:
    """
    Create and start a workspace container.
    Returns (container_id, workspace_url).
    """
    client = _client()
    subdomain = f"ws-{workspace.id}"
    url = f"https://{subdomain}.{settings.platform_domain}"

    volume_name = f"workspace-{workspace.id}"
    client.volumes.create(name=volume_name)

    container: Container = client.containers.run(
        _WORKSPACE_IMAGE,
        detach=True,
        name=str(workspace.id),
        network=_NETWORK,
        labels=_traefik_labels(subdomain),
        volumes={volume_name: {"bind": "/home/workspace", "mode": "rw"}},
        environment={
            "STUDENT_ID": str(workspace.student_id),
            "PROJECT_ID": str(workspace.project_id),
            "WORKSPACE_ID": str(workspace.id),
            "BACKEND_URL": settings.backend_url,
            "PROXY_URL": settings.proxy_url,
            "PLATFORM_TOKEN": _workspace_token(
                workspace.student_id, workspace.project_id, workspace.id
            ),
        },
        **_resource_kwargs(resource_overrides),
    )
    return container.id, url


def pause_container(container_id: str) -> None:
    client = _client()
    try:
        container = client.containers.get(container_id)
        container.pause()
    except NotFound:
        pass


def resume_container(container_id: str) -> None:
    client = _client()
    try:
        container = client.containers.get(container_id)
        container.unpause()
    except NotFound:
        pass


def stop_and_remove_container(container_id: str) -> None:
    client = _client()
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=10)
        container.remove()
    except NotFound:
        pass


def remove_volume(workspace_id: uuid.UUID) -> None:
    client = _client()
    volume_name = f"workspace-{workspace_id}"
    try:
        volume = client.volumes.get(volume_name)
        volume.remove()
    except NotFound:
        pass


def get_volume_path(workspace_id: uuid.UUID) -> str:
    """Return the Docker volume name for archiving."""
    return f"workspace-{workspace_id}"
