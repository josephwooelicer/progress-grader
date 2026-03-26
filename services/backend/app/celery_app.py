"""Celery app + background tasks."""
import io
import uuid
from datetime import datetime, timedelta, timezone

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery(
    "progress_grader",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    timezone="UTC",
    beat_schedule={
        "purge-old-archives-daily": {
            "task": "app.celery_app.purge_old_archives",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)


@celery.task(name="app.celery_app.archive_workspace_task")
def archive_workspace_task(workspace_id_str: str, skip_archive: bool = False) -> dict:
    """
    Archive workspace volume to Minio, then remove the Docker volume.
    Runs synchronously inside Celery worker process.
    """
    import asyncio
    import docker
    import boto3
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    workspace_id = uuid.UUID(workspace_id_str)

    if skip_archive:
        import docker as _docker
        _client = _docker.from_env()
        volume_name = f"workspace-{workspace_id}"
        try:
            vol = _client.volumes.get(volume_name)
            vol.remove()
        except Exception:
            pass
        return {"archived": False, "reason": "skipped"}

    # Sync DB engine for Celery task
    sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url)

    from app.models.workspace import Workspace, WorkspaceArchive

    with Session(engine) as session:
        workspace = session.get(Workspace, workspace_id)
        if not workspace:
            return {"error": "workspace not found"}

        volume_name = f"workspace-{workspace_id}"

        # Export volume via Docker API (create temporary container to tar volume)
        client = docker.from_env()
        container = client.containers.run(
            "alpine:3.19",
            command=f"tar czf /archive/backup.tar.gz -C /data .",
            volumes={
                volume_name: {"bind": "/data", "mode": "ro"},
                "archive-tmp": {"bind": "/archive", "mode": "rw"},
            },
            detach=False,
            remove=True,
        )

        # Read tar from temporary container's volume via another container
        out_container = client.containers.run(
            "alpine:3.19",
            command="cat /archive/backup.tar.gz",
            volumes={"archive-tmp": {"bind": "/archive", "mode": "ro"}},
            detach=False,
            remove=True,
        )
        archive_bytes = out_container

        # Upload to Minio
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.minio_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
        )
        minio_key = f"workspaces/{workspace.student_id}/{workspace_id}/backup.tar.gz"
        s3.put_object(
            Bucket=settings.minio_bucket,
            Key=minio_key,
            Body=archive_bytes,
        )
        size_bytes = len(archive_bytes)

        purge_after = datetime.now(timezone.utc) + timedelta(days=30)
        archive = WorkspaceArchive(
            id=uuid.uuid4(),
            student_id=workspace.student_id,
            project_id=workspace.project_id,
            minio_key=minio_key,
            size_bytes=size_bytes,
            purge_after=purge_after,
        )
        session.add(archive)
        session.commit()

    # Remove volume after successful archive
    try:
        vol = client.volumes.get(volume_name)
        vol.remove()
    except Exception:
        pass

    return {"archived": True, "minio_key": minio_key, "size_bytes": size_bytes}


@celery.task(name="app.celery_app.purge_old_archives")
def purge_old_archives() -> dict:
    """Delete Minio objects for archives past their purge_after date."""
    import boto3
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url)

    from app.models.workspace import WorkspaceArchive
    from sqlalchemy import select

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.minio_url,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    )

    purged = 0
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        result = session.execute(
            select(WorkspaceArchive).where(
                WorkspaceArchive.purge_after <= now,
                WorkspaceArchive.purged_at.is_(None),
            )
        )
        for archive in result.scalars().all():
            try:
                s3.delete_object(Bucket=settings.minio_bucket, Key=archive.minio_key)
                archive.purged_at = now
                purged += 1
            except Exception:
                pass
        session.commit()

    return {"purged": purged}
