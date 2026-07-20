# atlas/core/config_manager.py
import tomllib
from pathlib import Path
from typing import Dict, Any, List

class ConfigManager:
    """Gestiona la lectura y acceso a la configuración TOML de A.T.L.A.S"""
    
    def __init__(self, config_path: str = "config/global.toml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de configuración en {self.config_path}")
        with open(self.config_path, "rb") as f:
            return tomllib.load(f)

    def get_enabled_agents(self) -> Dict[str, Any]:
        agents = self.config.get("agentes", {})
        return {name: details for name, details in agents.items() if details.get("enabled", False)}

    def get_categories(self) -> List[str]:
        """Devuelve una lista de todas las categorías únicas de los agentes activos"""
        agents = self.get_enabled_agents()
        return list(set(details.get("categoria", "general") for details in agents.values()))

    def get_agents_by_category(self, category: str) -> Dict[str, Any]:
        """Devuelve los agentes activos que coinciden con la categoría"""
        agents = self.get_enabled_agents()
        return {name: details for name, details in agents.items() if details.get("categoria") == category}