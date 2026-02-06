"""Configuration module for nanobot."""

from lib.config.loader import load_config, get_config_path
from lib.config.schema import Config

__all__ = ["Config", "load_config", "get_config_path"]
