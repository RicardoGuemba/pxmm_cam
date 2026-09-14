"""Configuration validation with Pydantic."""

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class StreamingConfig(BaseModel):
    """Streaming section of config.yaml."""

    source_type: Literal["usb", "stapipy"] = Field(
        default="usb",
        description="Tipo de fonte: usb ou stapipy (Omron Sentech / StApi)",
    )
    usb_camera_index: int = Field(
        default=0,
        ge=0,
        description="Índice da câmera USB (0, 1, ...)",
    )
    device_index: int = Field(
        default=0,
        ge=0,
        description="Índice StApi (0 = create_first_device)",
    )
    fetch_timeout_ms: int = Field(
        default=400,
        ge=1,
        le=60000,
        description="Timeout de retrieve_buffer (ms)",
    )
    gige_ip: str = Field(
        default="",
        description="IP da câmera (metadado/diagnóstico; abertura StApi é por enumeração)",
    )
    gige_port: int = Field(
        default=3956,
        ge=1,
        le=65535,
        description="Porta GigE (legado/diagnóstico; não usada pelo StApi)",
    )
    gige_backend: str = Field(
        default="",
        description="Legado (ignorado); produção Sentech usa stapipy",
    )
    gentl_producer_path: str = Field(
        default="",
        description="Legado (ignorado); produção usa stapipy/SentechSDK, não .cti",
    )
    requested_width: Optional[int] = Field(
        default=None,
        ge=1,
        le=10000,
        description="Largura desejada do frame (opcional)",
    )
    requested_height: Optional[int] = Field(
        default=None,
        ge=1,
        le=10000,
        description="Altura desejada do frame (opcional)",
    )
    target_fps: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=1000.0,
        description="FPS alvo (opcional)",
    )

    @field_validator("source_type", mode="before")
    @classmethod
    def migrate_source_type(cls, v: object) -> object:
        if v == "gige":
            return "stapipy"
        return v

    @field_validator("gige_ip", mode="before")
    @classmethod
    def coerce_gige_ip(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v).strip()


class UIConfig(BaseModel):
    """UI section of config.yaml."""

    auto_export: bool = Field(default=False, description="Exportar automaticamente ao medir")


class ExportConfig(BaseModel):
    """Export section of config.yaml."""

    default_dir: str = Field(default="", description="Diretório padrão para export CSV/JSON")


class AppConfig(BaseModel):
    """Root configuration model."""

    streaming: StreamingConfig = Field(default_factory=StreamingConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)


def load_config(path: Optional[Path] = None) -> AppConfig:
    """Load and validate config from YAML file.

    Args:
        path: Path to config.yaml. If None, tries project root and package config.

    Returns:
        Validated AppConfig.

    Raises:
        FileNotFoundError: If no config file found.
        ValidationError: If config is invalid.
    """
    if path is None:
        candidates = [
            Path(__file__).resolve().parent.parent.parent / "config.yaml",
            Path(__file__).resolve().parent / "config.yaml",
            Path("config.yaml"),
        ]
        for p in candidates:
            if p.is_file():
                path = p
                break
        else:
            raise FileNotFoundError(
                "Arquivo config.yaml não encontrado. Procure em: "
                + ", ".join(str(p) for p in candidates)
            )
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Config não encontrado: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}
    return AppConfig.model_validate(data)
