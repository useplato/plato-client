"""
Configuration models for Plato simulators.

This module contains Pydantic models that define the structure of simulator
configuration files (plato-config.yml) and related configuration objects.
"""

from typing import Optional, Dict, List, Any, Union, Literal
from abc import ABC
from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    model_validator,
    model_serializer,
)
from pydantic_core import PydanticCustomError


class AdaptiveObject(BaseModel, ABC):
    """An abstract object that may be one of several concrete types."""

    @model_validator(mode="wrap")
    @classmethod
    def _resolve_adaptive_object(cls, data: Any, handler) -> Any:
        try:
            data = dict(data)
        except Exception as e:
            raise PydanticCustomError(
                "adaptive-object", "Data is not a dictionary"
            ) from e

        # if cls is not abstract, there's nothing to do
        if ABC not in cls.__bases__:
            return handler(data)

        # try to validate the data for each possible type
        possible_types = sorted(
            list(cls._find_all_possible_types()),
            key=lambda x: len(x.__annotations__),
            reverse=True,
        )
        for subcls in possible_types:
            try:
                # return the first successful validation
                return subcls.model_validate(data)
            except ValidationError:
                continue

        message = "Could not resolve input to a valid type. Possible types: "
        message += ", ".join([subcls.__name__ for subcls in possible_types])
        raise PydanticCustomError(
            "adaptive-object",
            message,  # type: ignore
        )

    @classmethod
    def _find_all_possible_types(cls):
        """Recursively generate all possible types for this object."""

        # any concrete class is a possible type
        if ABC not in cls.__bases__:
            yield cls

        # continue looking for possible types in subclasses
        for subclass in cls.__subclasses__():
            yield from subclass._find_all_possible_types()

    def instantiate(self):
        # check if _target_ is set
        if not hasattr(self, "_target_"):
            raise ValueError(
                "Model does not have a _target_ attribute. Cannot instantiate."
            )
        # instantiate the target
        from hydra.utils import instantiate

        cfg = self.model_dump(mode="json")
        cfg["_target_"] = self._target_  # type: ignore
        return instantiate(cfg)

    @model_serializer
    def _serialize(self):
        data = {}
        for key in self.model_fields.keys():
            value = getattr(self, key)
            if isinstance(value, BaseModel):
                data[key] = value.model_dump(mode="json")
            elif isinstance(value, list):
                data[key] = [
                    v.model_dump(mode="json") if isinstance(v, BaseModel) else v
                    for v in value
                ]
            else:
                data[key] = value
        return data


class SimConfigCompute(BaseModel):
    """Compute resource configuration for a simulator."""

    cpus: int = Field(description="vCPUs", ge=1, le=8, default=1)
    memory: int = Field(description="Memory in MB", ge=512, le=16384, default=2048)
    disk: int = Field(description="Disk space in MB", ge=1024, le=102400, default=10240)
    app_port: int = Field(
        description="Application port", ge=0, le=65535, default=8080
    )
    plato_messaging_port: int = Field(
        description="Plato messaging port", ge=0, le=65535, default=7000
    )


class SimConfigMetadata(BaseModel):
    """Metadata configuration for a simulator."""

    favicon: str = Field(
        description="Favicon URL", default="https://plato.so/favicon.ico"
    )
    name: str = Field(description="Name", default="Plato")
    description: str = Field(
        description="Description",
        default="Plato is a platform for building and running simulations.",
    )
    source_code_url: str = Field(
        description="Source code URL", default="https://github.com/plato/plato"
    )
    start_url: str = Field(description="Start URL", default="https://plato.so")
    license: str = Field(description="License", default="MIT")
    variables: list[dict[str, str]] = Field(
        description="Variables", default=[{"name": "PLATO_API_KEY", "value": "plato"}]
    )
    flows_path: Optional[str] = Field(default=None, description="Flows path")


class SimConfigService(AdaptiveObject, ABC):
    """Base class for simulator service configurations."""

    type: Literal["docker-compose", "docker"] = Field(description="Service type")


class DockerComposeServiceConfig(SimConfigService):
    """Configuration for Docker Compose based services."""

    type: Literal["docker-compose"] = Field(
        description="Service type", default="docker-compose"
    )
    file: str = Field(default="docker-compose.yml", description="Entrypoint file path")
    required_healthy_containers: List[str] = Field(
        default=["*"],
        description="List of services to wait for (use ['*'] for all services)",
    )
    healthy_wait_timeout: int = Field(
        default=300,
        ge=30,
        le=1800,
        description="Timeout in seconds to wait for services to become healthy",
    )


class SimConfigListener(AdaptiveObject, ABC):
    """Base class for mutation listener configurations."""

    type: Literal["db", "proxy", "file"] = Field(description="Listener type")


class DatabaseMutationListenerConfig(SimConfigListener):
    """Configuration for database mutation listeners."""

    type: Literal["db"] = Field(description="Listener type")
    db_type: Literal["postgresql", "mysql", "sqlite"] = Field(
        description="Database type"
    )
    db_host: str = Field(description="Database host")
    db_port: int = Field(ge=1, le=65535, description="Database port")
    db_user: str = Field(description="Database user")
    db_password: str = Field(description="Database password")
    db_database: str = Field(description="Database name")
    schema: Optional[str] = Field(
        default="public", description="Database schema (for PostgreSQL)"
    )
    seed_data_paths: Optional[List[str]] = Field(
        default=None, description="Seed data paths"
    )
    truncate_tables: Optional[bool] = Field(
        default=None, description="Truncate tables before seed restore"
    )
    audit_ignore_tables: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        default=None, description="Tables or patterns the auditor should ignore"
    )
    volumes: Optional[List[str]] = Field(default=None, description="Volumes to mount")


class ProxyMutationListenerConfig(SimConfigListener):
    """Configuration for proxy mutation listeners."""

    type: Literal["proxy"] = Field(description="Listener type")
    sim_name: Optional[str] = Field(default=None, description="Name of the simulation")
    dataset: Optional[str] = Field(default=None, description="Dataset to use")
    proxy_host: str = Field(default="localhost", description="Proxy server host")
    proxy_port: int = Field(
        default=8888, ge=1024, le=65535, description="Proxy server port"
    )
    passthrough_all_ood_requests: bool = Field(
        default=True, description="Whether to pass through out-of-domain requests"
    )
    replay_sessions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Replay sessions configuration"
    )


class SimConfigFileMutationListener(SimConfigListener):
    """Configuration for file mutation listeners."""

    type: Literal["file"] = Field(description="Listener type")
    seed_data_path: Optional[str] = Field(default=None, description="Seed data path")
    target_dir: str = Field(description="Main directory for file monitoring")
    watch_enabled: bool = Field(default=True, description="Enable mutation tracking")
    watch_patterns: Optional[List[str]] = Field(
        default_factory=lambda: ["*"], description="Glob patterns to watch"
    )
    ignore_patterns: Optional[List[str]] = Field(
        default_factory=list, description="Glob patterns to ignore"
    )
    scan_frequency: int = Field(
        default=5, description="State rescan frequency in seconds"
    )
    volumes: Optional[List[str]] = Field(default=None, description="Volumes to mount")


class SimConfigDataset(BaseModel):
    """Configuration for a simulator dataset."""

    compute: SimConfigCompute = Field(description="Compute configuration")
    metadata: SimConfigMetadata = Field(description="Metadata configuration")
    services: Optional[dict[str, SimConfigService]] = Field(description="Services")
    listeners: Optional[dict[str, SimConfigListener]] = Field(description="Listeners")


class SimConfig(BaseModel):
    """Root configuration model for simulators."""

    datasets: dict[str, SimConfigDataset] = Field(description="Datasets")
