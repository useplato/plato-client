"""
Configuration models for Plato Builder CLI
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field


class AuditIgnoreTable(BaseModel):
    """Table configuration for audit ignore settings"""
    table: str
    columns: Optional[List[str]] = None


class DatabaseConfig(BaseModel):
    """Database configuration"""
    db_type: str
    db_version: str
    db_host: str = Field(default="0.0.0.0")
    db_port: int = Field(default=5432)
    db_user: str
    db_password: str
    db_database: str
    seed_data_paths: Optional[List[str]] = None
    truncate_tables: Optional[bool] = None
    audit_ignore_tables: Optional[List[Union[str, AuditIgnoreTable]]] = None


class PlatoConfig(BaseModel):
    """Plato-specific configuration"""
    sim_name: str
    messaging_port: int = Field(default=7000, description="Reserved port for Plato messaging")
    access_port: int = Field(default=8080, description="External access port")
    vcpus: int = Field(default=1)
    memory: int = Field(default=2048, description="Memory in MB")
    storage: int = Field(default=8192, description="Storage in MB")


class EnvironmentConfig(BaseModel):
    """Complete environment configuration from env.yml"""
    db: Optional[DatabaseConfig] = None
    plato: PlatoConfig 
    
    # Allow additional fields for custom configurations
    model_config = {"extra": "allow"}


class VMJob(BaseModel):
    """VM Job representation"""
    uuid: str
    name: str
    status: str
    time_started: str
    url: Optional[str] = None


class CreateVMRequest(BaseModel):
    """Request model for creating a VM"""
    service: str
    version: str = "latest"
    alias: Optional[str] = None
    vcpu_count: int = 1
    mem_size_mib: int = 2048
    overlay_size_mb: int = 8192
    port: int = 8080
    wait_time: int = 30
    vm_timeout: int = 1800
    messaging_port: int = 7000


class VMCreationResponse(BaseModel):
    """Response model for VM creation"""
    uuid: str
    name: str
    status: str
    time_started: str
    url: str
    correlation_id: str
    sse_stream_url: str
    job_public_id: str
    job_group_id: str


class ConfigureVMRequest(BaseModel):
    """Request model for configuring a VM"""
    job_uuid: str
    compose_file_path: str
    env_config_path: str


class VMConfigurationResponse(BaseModel):
    """Response model for VM configuration"""
    job_uuid: str
    compose_file: str
    env_config: str
    configured_at: str
    message: str
