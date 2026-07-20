# atlas/core/brain.py
import os
import json
from typing import List, Dict, Any, AsyncGenerator, cast
from dotenv import load_dotenv
from groq import AsyncGroq
from groq.types.chat import ChatCompletionMessageParam

load_dotenv()

class AtlasBrain:
    """El cerebro de A.T.L.A.S"""
    
    def __init__(self, max_history: int = 8):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Error: No se encontró la GROQ_API_KEY en el archivo .env")
        self.client = AsyncGroq(api_key=api_key)
        self.max_history = max_history

    async def route_message(self, user_message: str, categories: List[str]) -> Dict[str, Any]:
        """Analiza el mensaje y decide si es charla o requiere una acción por categoría"""
        
        system_prompt = fsystem_prompt = f"""Eres el router de A.T.L.A.S. Clasifica el mensaje del usuario.
Categorías disponibles: {categories}

REGLAS:
- Si el usuario pide CUALQUIER acción en el sistema (controlar volumen, brillo, batería, abrir apps, Safari, archivos, terminal, capturas, notificaciones, procesos, red, portapapeles, etc.), es una ACCIÓN.
- Si el usuario pregunta información sobre el sistema (batería, CPU, disco, IP, etc.), es una ACCIÓN.
- Solo es chat si el usuario quiere conversar, preguntar conocimientos generales o pedir consejos.

Ejemplos de ACCIONES:
- "baja el volumen" → action
- "estado de la bateria" → action
- "abre Safari" → action
- "dime la ip" → action
- "haz una captura" → action

Si es acción, responde:
{{"type": "action", "category": "ejecucion", "query": "..."}}

Si es chat, responde:
{{"type": "chat"}}"""
        
        # Definimos la herramienta para detectar acciones
        tools = [{
            "type": "function",
            "function": {
                "name": "detect_action",
                "description": "Se usa cuando el usuario pide una acción técnica específica.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": categories, "description": "La categoría de la acción solicitada"},
                        "query": {"type": "string", "description": "La consulta o tarea refinada para el agente"}
                    },
                    "required": ["category", "query"]
                }
            }
        }]

        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response = await self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,  # type: ignore[arg-type]
            tools=tools,  # type: ignore[arg-type]
            tool_choice="auto",
        )
        
        choice = response.choices[0]
        
        # Si llama a la herramienta, es una acción
        if choice.message.tool_calls:
            args = json.loads(choice.message.tool_calls[0].function.arguments)
            return {
                "type": "action",
                "category": args["category"],
                "query": args["query"]
            }
        
        # Si responde texto, es charla
        return {
            "type": "chat",
            "content": choice.message.content
        }

    async def think_stream(self, user_message: str, history: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
        """Genera la respuesta en streaming"""
        system_prompt = "Eres A.T.L.A.S, un asistente de terminal avanzado. Usa formato Markdown."
        recent_history = history[-self.max_history:] if len(history) > self.max_history else history
        
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt}
        ]
        messages.extend(cast(List[ChatCompletionMessageParam], recent_history))
        messages.append({"role": "user", "content": user_message})
        
        stream = await self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,  # type: ignore[arg-type]
            temperature=0.7,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content