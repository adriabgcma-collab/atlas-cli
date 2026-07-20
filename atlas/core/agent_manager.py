# atlas/core/agent_manager.py
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Any

class AgentManager:
    """Gestiona el ciclo de vida efímero de los agentes independientes"""
    
    def __init__(self, logger):
        self.logger = logger

    async def execute(self, agent_name: str, agent_config: Dict[str, Any], query: str) -> str:
        """Ejecuta un agente, le pasa la consulta y devuelve su respuesta"""
        
        # 1. Generar una ruta de socket única para esta ejecución
        socket_path = f"/tmp/atlas_{agent_name}_{uuid.uuid4().hex}.sock"
        
        # 2. Preparar el comando (ej: "python agents/template/server.py /tmp/...sock")
        command_parts = agent_config["comando"].split()
        command_parts.append(socket_path)
        
        self.logger.info("agent_manager", f"Lanzando agente: {agent_name} | Comando: {' '.join(command_parts)}")
        
        # 3. Lanzar el proceso en segundo plano
        try:
            process = await asyncio.create_subprocess_exec(
                *command_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except Exception as e:
            self.logger.error("agent_manager", f"Error al lanzar el proceso: {str(e)}")
            return f"Error al iniciar el agente: {str(e)}"

        # 4. Esperar a que el socket exista (con un timeout de 3 segundos)
        timeout = 3
        waited = 0
        while not os.path.exists(socket_path) and waited < timeout:
            await asyncio.sleep(0.1)
            waited += 0.1
            
        if not os.path.exists(socket_path):
            process.terminate()
            self.logger.error("agent_manager", "El agente no creó el socket a tiempo.")
            return "Error: El agente no respondió a tiempo."

        # 5. Conectarse al socket y enviar la petición
        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)
            
            request = {"action": "execute", "query": query}
            writer.write(json.dumps(request).encode('utf-8'))
            await writer.drain()
            
            # 6. Leer la respuesta (con timeout según la config del agente)
            max_timeout = agent_config.get("timeout", 30)
            try:
                data = await asyncio.wait_for(reader.read(8192), timeout=max_timeout)
                response = json.loads(data.decode('utf-8'))
                
                output = response.get("output", "El agente no devolvió un output válido.")
                self.logger.info("agent_manager", f"Agente {agent_name} respondió con éxito.")
                return output
                
            except asyncio.TimeoutError:
                self.logger.error("agent_manager", f"Timeout esperando respuesta del agente {agent_name}")
                return f"Error: El agente {agent_name} tardó demasiado en responder."
                
        except Exception as e:
            self.logger.error("agent_manager", f"Error de comunicación con el agente: {str(e)}")
            return f"Error de comunicación: {str(e)}"
            
        finally:
            # 7. Limpieza: Cerrar conexión, matar proceso y borrar socket
            if 'writer' in locals() and writer:
                writer.close()
                await writer.wait_closed()
                
            process.terminate()
            try:
                await process.wait()
            except ProcessLookupError:
                pass # El proceso ya terminó
                
            if os.path.exists(socket_path):
                os.remove(socket_path)
                
            self.logger.info("agent_manager", f"Agente {agent_name} finalizado y limpiado.")