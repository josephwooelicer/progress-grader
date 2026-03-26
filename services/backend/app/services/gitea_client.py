"""Gitea HTTP API client."""
import base64
import uuid
from typing import Any

import httpx

from app.config import settings

_HEADERS = {"Content-Type": "application/json"}


def _auth_headers() -> dict[str, str]:
    return {**_HEADERS, "Authorization": f"token {settings.gitea_admin_token}"}


def _url(path: str) -> str:
    return f"{settings.gitea_url}/api/v1{path}"


async def create_org(org_name: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _url("/orgs"),
            json={"username": org_name, "visibility": "private"},
            headers=_auth_headers(),
        )
        if resp.status_code not in (201, 422):  # 422 = already exists
            resp.raise_for_status()


async def create_repo(org: str, repo_name: str) -> str:
    """Create a private repo in the org. Returns clone URL."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _url(f"/orgs/{org}/repos"),
            json={"name": repo_name, "private": True, "auto_init": False},
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()["clone_url"]


async def create_user_token(gitea_username: str, token_name: str) -> str:
    """Generate a Gitea access token for a student user. Returns raw token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _url(f"/users/{gitea_username}/tokens"),
            json={"name": token_name},
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()["sha1"]


async def add_collaborator(org: str, repo_name: str, gitea_username: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            _url(f"/repos/{org}/{repo_name}/collaborators/{gitea_username}"),
            json={"permission": "write"},
            headers=_auth_headers(),
        )
        resp.raise_for_status()


async def register_webhook(org: str, repo_name: str, webhook_url: str, secret: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _url(f"/repos/{org}/{repo_name}/hooks"),
            json={
                "type": "gitea",
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "secret": secret,
                },
                "events": ["push", "create", "delete", "pull_request"],
                "active": True,
            },
            headers=_auth_headers(),
        )
        resp.raise_for_status()


async def initial_commit(
    org: str,
    repo_name: str,
    skeleton_files: dict[str, str],
) -> None:
    """Push skeleton files as the initial commit via Gitea Contents API."""
    async with httpx.AsyncClient() as client:
        for path, content in skeleton_files.items():
            encoded = base64.b64encode(content.encode()).decode()
            resp = await client.post(
                _url(f"/repos/{org}/{repo_name}/contents/{path}"),
                json={
                    "message": f"chore: add {path}",
                    "content": encoded,
                },
                headers=_auth_headers(),
            )
            resp.raise_for_status()


async def ensure_gitea_user(email: str, username: str, password: str) -> None:
    """Create a Gitea user if they don't exist."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _url("/admin/users"),
            json={
                "email": email,
                "login_name": username,
                "username": username,
                "password": password,
                "must_change_password": False,
            },
            headers=_auth_headers(),
        )
        if resp.status_code not in (201, 422):  # 422 = already exists
            resp.raise_for_status()
