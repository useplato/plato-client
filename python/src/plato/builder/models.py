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
    access_port: int = Field(default=80, description="External access port")
    vcpus: int = Field(default=1)
    memory: int = Field(default=2048, description="Memory in MB")
    storage: int = Field(default=10480, description="Storage in MB")


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
