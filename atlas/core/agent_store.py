# atlas/core/agent_store.py
import json
import os
import sys
import subprocess
import shutil
import tomllib
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional

class AgentStore:
    """Gestiona la descarga, instalación y actualización de agentes desde un repositorio remoto"""
    
    def __init__(self, config_path: str = "config/global.toml"):
        self.config_path = Path(config_path)
        self.agents_dir = Path("agents")
        self.agents_dir.mkdir(exist_ok=True)
        
        # Cargar configuración actual
        with open(self.config_path, "rb") as f:
            self.config = tomllib.load(f)
            
        self.manifest_url = self.config.get("store", {}).get("manifest_url")
        self.installed_agents = self.config.get("agentes", {})

    async def fetch_manifest(self) -> Optional[List[Dict[str, Any]]]:
        """Descarga el manifiesto JSON desde la URL configurada"""
        if not self.manifest_url:
            return None
        try:
            with urllib.request.urlopen(self.manifest_url) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data.get("agents", [])
        except Exception as e:
            print(f"[Store] Error al descargar manifiesto: {e}")
            return None

    def install_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Descarga e instala un agente. Devuelve un dict con el resultado y dependencias pendientes."""
        agent_id = agent_data["id"]
        zip_url = agent_data.get("zip_url")
        dependencies = agent_data.get("dependencies", [])
        
        if not zip_url:
            return {"success": False, "error": "No hay URL de descarga para este agente."}

        # 1. Descargar ZIP
        local_zip = self.agents_dir / f"{agent_id}.zip"
        try:
            urllib.request.urlretrieve(zip_url, local_zip)
        except Exception as e:
            return {"success": False, "error": f"Error al descargar ZIP: {e}"}

        # 2. Descomprimir en agents/{agent_id}/
        agent_dir = self.agents_dir / agent_id
        agent_dir.mkdir(exist_ok=True)
        try:
            with zipfile.ZipFile(local_zip, 'r') as zip_ref:
                zip_ref.extractall(agent_dir)
            local_zip.unlink() # Borrar ZIP tras extraer
        except Exception as e:
            return {"success": False, "error": f"Error al descomprimir: {e}"}

        # 2.5. Limpiar basura de macOS (__MACOSX y archivos ._)
        macosx_dir = agent_dir / "__MACOSX"
        if macosx_dir.exists():
            shutil.rmtree(macosx_dir)
        for hidden_file in agent_dir.rglob("._*"):
            try:
                hidden_file.unlink()
            except Exception:
                pass

        # 3. Actualizar global.toml (añadir o actualizar la sección del agente)
        if agent_id not in self.installed_agents:
            self.installed_agents[agent_id] = {
                "nombre": agent_data.get("name", agent_id.upper()),
                "categoria": agent_data.get("category", "general"),
                "etiquetas": agent_data.get("tags", []),
                "comando": f"python agents/{agent_id}/server.py",
                "descripcion": agent_data.get("description", ""),
                "enabled": True,
                "timeout": 30,
                "version": agent_data.get("version", "1.0.0")
            }
            self._save_config()

        # 4. Devolver dependencias para que la UI pregunte
        return {
            "success": True, 
            "agent_id": agent_id, 
            "dependencies": dependencies
        }

    def install_dependencies(self, dependencies: List[str]) -> Dict[str, Any]:
        """Ejecuta pip install para las dependencias dadas"""
        if not dependencies:
            return {"success": True, "message": "Sin dependencias."}
            
        try:
            # Usar el mismo python que ejecuta la app
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + dependencies)
            return {"success": True, "message": f"Dependencias instaladas: {', '.join(dependencies)}"}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": f"Error instalando dependencias: {e}"}

    def _save_config(self):
        """Guarda los cambios en el TOML"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write("# config/global.toml\n\n")
            f.write("[groq]\n")
            f.write(f'model = "{self.config.get("groq", {}).get("model", "llama-3.3-70b-versatile")}"\n')
            f.write(f'temperature = {self.config.get("groq", {}).get("temperature", 0.7)}\n\n')
            
            f.write("[store]\n")
            f.write(f'manifest_url = "{self.manifest_url}"\n\n')
            
            f.write("[agentes]\n")
            for agent_id, details in self.installed_agents.items():
                f.write(f"[agentes.{agent_id}]\n")
                for k, v in details.items():
                    if isinstance(v, bool):
                        f.write(f'{k} = {"true" if v else "false"}\n')
                    elif isinstance(v, list):
                        f.write(f'{k} = {json.dumps(v)}\n')
                    elif isinstance(v, str):
                        f.write(f'{k} = "{v}"\n')
                    else:
                        f.write(f'{k} = {v}\n')
                f.write("\n")