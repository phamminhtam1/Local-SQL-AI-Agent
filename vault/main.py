from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

import hvac
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import dotenv


dotenv.load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    VAULT_ADDR: Vault URL, e.g. http://127.0.0.1:8200
    VAULT_TOKEN: Vault token with access to the KV v2 mount
    VAULT_MOUNT: Name of the KV v2 mount (default: "secret")
    VAULT_BASE_PATH: Base path under the mount to store credentials
                     (default: "credentials"). Ignored when
                     VAULT_USE_USER_BASE is true.
    VAULT_USE_USER_BASE: If true, treat each user's id as the base path,
                         storing at "{user_id}/{name}". If false, use
                         "{VAULT_BASE_PATH}/{user_id}/{name}".
    """

    vault_addr: str = Field(default_factory=lambda: os.getenv("VAULT_ADDR", "http://127.0.0.1:8200"))
    vault_token: str = Field(default_factory=lambda: os.getenv("VAULT_TOKEN", ""))
    vault_mount: str = Field(default_factory=lambda: os.getenv("VAULT_MOUNT", "secret"))
    vault_base_path: str = Field(default_factory=lambda: os.getenv("VAULT_BASE_PATH", "credentials"))
    use_user_as_base: bool = Field(
        default_factory=lambda: os.getenv("VAULT_USE_USER_BASE", "true").lower()
        in ("1", "true", "yes", "y")
    )


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    if not settings.vault_token:
        raise RuntimeError("VAULT_TOKEN is required")
    return settings


def get_vault_client(settings: Settings = Depends(get_settings)) -> hvac.Client:
    client = hvac.Client(url=settings.vault_addr, token=settings.vault_token)
    if not client.is_authenticated():
        raise RuntimeError("Failed to authenticate to Vault")
    return client


class SecretCreate(BaseModel):
    """Model for creating a new secret."""

    name: str = Field(..., min_length=1, max_length=128)
    user_id: str = Field(..., min_length=1, max_length=256)
    data: Dict[str, Any] = Field(..., description="Arbitrary key/value pairs")


class SecretInfo(BaseModel):
    """Metadata about a secret; values omitted by default."""

    path: str
    name: str
    user_id: str
    version: Optional[int] = None
    created_time: Optional[str] = None
    updated_time: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


app = FastAPI(title="Vault Credentials Service", version="0.1.0")


def _credential_path(user_id: str, name: str, settings: Settings) -> str:
    if settings.use_user_as_base:
        return f"{user_id}/{name}"
    return f"{settings.vault_base_path}/{user_id}/{name}"


def _list_recursive_kv2(
    client: hvac.Client, mount: str, base_path: str
) -> List[str]:
    """Recursively list all leaf paths under a KV v2 mount/path."""

    results: List[str] = []

    def walk(prefix: str) -> None:
        try:
            resp = client.secrets.kv.v2.list_secrets(
                mount_point=mount, path=prefix
            )
        except (hvac.exceptions.InvalidPath, hvac.exceptions.Forbidden):
            return
        except Exception:
            # Handle any other hvac exceptions gracefully
            return

        keys = resp.get("data", {}).get("keys", [])
        for key in keys:
            if key.endswith("/"):
                walk(prefix + key)
            else:
                results.append(prefix + key)

    if base_path:
        walk(base_path if base_path.endswith("/") else base_path + "/")
    else:
        walk("")
    return results


def _read_secret_info(
    client: hvac.Client, mount: str, path: str, include_values: bool
) -> SecretInfo:
    try:
        resp = client.secrets.kv.v2.read_secret_version(
            mount_point=mount, path=path
        )
    except (hvac.exceptions.InvalidPath, hvac.exceptions.Forbidden) as e:
        raise HTTPException(status_code=404, detail=f"Secret not found: {path}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading secret: {str(e)}") from e

    data = resp.get("data", {})
    metadata = data.get("metadata", {})
    values = data.get("data", {}) if include_values else None

    # Expect stored at credentials/{user_id}/{name}
    parts = path.split("/")
    name = parts[-1]
    user_id = parts[-2] if len(parts) >= 2 else ""

    return SecretInfo(
        path=path,
        name=name,
        user_id=user_id,
        version=metadata.get("version"),
        created_time=metadata.get("created_time"),
        updated_time=metadata.get("updated_time"),
        data=values,
    )


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/secrets", response_model=List[SecretInfo])
def list_secrets(
    user_id: Optional[str] = Query(None, description="Filter by user_id"),
    include_values: bool = Query(
        True, description="Include secret values in response"
    ),
    client: hvac.Client = Depends(get_vault_client),
    settings: Settings = Depends(get_settings),
) -> List[SecretInfo]:

    if user_id is not None and settings.use_user_as_base:
        base = f"{user_id}"
    elif user_id is not None:
        base = f"{settings.vault_base_path}/{user_id}"
    else:
        base = settings.vault_base_path if not settings.use_user_as_base else ""

    paths = _list_recursive_kv2(client, settings.vault_mount, base)
    infos: List[SecretInfo] = []
    for path in paths:
        try:
            infos.append(
                _read_secret_info(
                    client, settings.vault_mount, path, include_values
                )
            )
        except HTTPException:
            # Skip secrets that can't be read
            continue
    return infos


@app.get("/secrets/{user_id}/{name}", response_model=SecretInfo)
def get_secret(
    user_id: str,
    name: str,
    include_values: bool = Query(
        True, description="Include secret values in response"
    ),
    client: hvac.Client = Depends(get_vault_client),
    settings: Settings = Depends(get_settings),
) -> SecretInfo:
    path = _credential_path(user_id=user_id, name=name, settings=settings)
    return _read_secret_info(
        client, settings.vault_mount, path, include_values
    )


@app.post("/secrets", response_model=SecretInfo, status_code=201)
def create_secret(
    payload: SecretCreate,
    allow_overwrite: bool = Query(
        False, description="Allow overwriting existing secret"
    ),
    client: hvac.Client = Depends(get_vault_client),
    settings: Settings = Depends(get_settings),
) -> SecretInfo:
    path = _credential_path(
        user_id=payload.user_id, name=payload.name, settings=settings
    )

    # Check duplicate unless overwrite permitted
    try:
        client.secrets.kv.v2.read_secret_version(
            mount_point=settings.vault_mount, path=path
        )
        exists = True
    except (hvac.exceptions.InvalidPath, hvac.exceptions.Forbidden):
        exists = False
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking existing secret: {str(e)}"
        ) from e

    if exists and not allow_overwrite:
        raise HTTPException(
            status_code=409,
            detail="Secret already exists; set allow_overwrite=true to replace",
        )

    # Persist secret
    try:
        # Use cas=0 for create operation if not overwriting
        cas = None if allow_overwrite else 0
        client.secrets.kv.v2.create_or_update_secret(
            mount_point=settings.vault_mount,
            path=path,
            secret=payload.data,
            cas=cas if not exists else None
        )
    except hvac.exceptions.InvalidRequest as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid request to Vault: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating secret: {str(e)}"
        ) from e

    # Return metadata (and values for clarity on create)
    return _read_secret_info(
        client,
        settings.vault_mount,
        path,
        include_values=True,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )