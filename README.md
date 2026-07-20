# 🏛️ A.T.L.A.S
### Automated Task Lifecycle & Agent Supervisor

**A.T.L.A.S** es un asistente de terminal inteligente para macOS que combina el poder de la IA (Groq) con un sistema modular de agentes especializados. Controla tu Mac con lenguaje natural, instala nuevos agentes desde una tienda centralizada y automatiza tareas complejas con una simple frase.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![macOS](https://img.shields.io/badge/macOS-12+-silver)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Características

- 🧠 **IA Integrada**: Usa Groq (Llama 3.3) para entender lenguaje natural
- 🛒 **Tienda de Agentes**: Descarga e instala agentes desde GitHub con un comando
- 🔌 **Arquitectura Modular**: Cada agente es independiente y se comunica por sockets UNIX
- 🛡️ **Seguridad**: Listas negras de procesos y rutas protegidas
- 🎨 **UI Terminal Moderna**: Interfaz construida con Textual
- 📦 **Gestión Automática de Dependencias**: Instala lo que necesita cada agente
- ⚡ **Comandos Compuestos**: Ejecuta múltiples acciones en una sola frase

---

## 🚀 Instalación

### Requisitos
- **macOS 12+** (usa AppleScript para control del sistema)
- **Python 3.10+**
- **API Key de Groq** (gratuita en [console.groq.com](https://console.groq.com))

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/adriabgcma-collab/atlas-cli.git
cd atlas-cli

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar A.T.L.A.S
python -m atlas.main
```

En la primera ejecución, A.T.L.A.S te guiará para configurar tu API Key de Groq y te abrirá automáticamente la tienda para que instales tu primer agente.

---

## 🎮 Uso

### Comandos básicos

| Comando | Descripción |
|---------|-------------|
| `/tienda` | Abre la tienda de agentes |
| `/ayuda` | Muestra la ayuda |
| `/clear` | Limpia el chat |
| `/cancelar` | Cancela la acción en curso |

### Ejemplos con T.I.T.A.N

Una vez instalado T.I.T.A.N (el agente base), puedes decirle cosas como:

```
🗣️ "Abre Safari y ve a youtube.com"
🗣️ "Baja el volumen al 20%"
🗣️ "Dime el estado de la batería"
🗣️ "Crea una carpeta llamada 'Proyectos' en el Escritorio"
🗣️ "Haz una captura de pantalla"
🗣️ "Muestra una notificación que diga 'Tarea completada'"
🗣️ "Copia 'Hola mundo' al portapapeles"
🗣️ "Dime tu IP pública"
```

T.I.T.A.N entiende lenguaje natural gracias a Groq, así que no necesitas memorizar comandos exactos.

---

## 🤖 Agentes Disponibles

### T.I.T.A.N (Terminal Integration & Task Automation Network)
El agente base recomendado. Control total del sistema macOS con **24 comandos**:

| Categoría | Comandos |
|-----------|----------|
| 🌐 **Safari** | `safari_abrir`, `safari_navegar` |
| 📁 **Archivos** | `archivo_crear`, `archivo_mover`, `archivo_buscar` |
| 📂 **Carpetas** | `carpeta_crear`, `carpeta_listar` |
| 🖥️ **Apps** | `app_abrir`, `app_cerrar` |
| ⚙️ **Sistema** | `sistema_volumen`, `sistema_brillo`, `sistema_bateria`, `sistema_info`, `sistema_wifi`, `sistema_bluetooth`, `sistema_captura`, `sistema_notificacion` |
| 🔄 **Procesos** | `proceso_listar`, `proceso_matar` |
| 🌐 **Red** | `red_ping`, `red_ip_publica` |
| 📺 **Finder** | `finder_abrir` |
| 🪟 **Ventanas** | `ventana_minimizar` |
| 🎵 **Medios** | `media_play_pause`, `media_siguiente`, `media_anterior` |
| 📋 **Portapapeles** | `portapapeles_leer`, `portapapeles_escribir` |
| 💻 **Terminal** | `terminal_ejecutar` |
| 🕐 **Utilidades** | `utilidad_fecha` |

---

## 🛠️ Crear tu propio agente

Crear un agente nuevo es sencillo. Solo necesitas:

### 1. Estructura mínima
```
agents/mi_agente/
└── server.py
```

### 2. Plantilla de `server.py`
```python
import socket
import json
import sys
import os
import asyncio

class MiAgente:
    def __init__(self):
        pass
    
    async def procesar_query(self, query: str) -> str:
        # Tu lógica aquí
        return f"Respuesta a: {query}"
    
    def start_unix_server(self, socket_path: str):
        if os.path.exists(socket_path):
            os.remove(socket_path)
        
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(socket_path)
        server.listen(1)
        
        conn, _ = server.accept()
        try:
            data = conn.recv(65536)
            if data:
                request = json.loads(data.decode('utf-8'))
                loop = asyncio.new_event_loop()
                response = loop.run_until_complete(self.procesar_query(request["query"]))
                loop.close()
                
                payload = {"response": response, "output": response}
                conn.sendall(json.dumps(payload).encode('utf-8'))
        finally:
            conn.close()
            server.close()
            sys.exit(0)

if __name__ == "__main__":
    socket_path = sys.argv[1]
    MiAgente().start_unix_server(socket_path)
```

### 3. Publicar en la tienda
1. Crea un ZIP limpio: `zip -r -X mi_agente.zip .`
2. Súbelo a tu repositorio de agentes
3. Añade una entrada en tu `manifest.json`:

```json
{
  "id": "mi_agente",
  "name": "MI.AGENTE",
  "category": "mi_categoria",
  "description": "Descripción de lo que hace",
  "version": "1.0.0",
  "zip_url": "https://raw.githubusercontent.com/.../mi_agente.zip",
  "dependencies": []
}
```

4. Configura la URL del manifiesto en `config/global.toml`:
```toml
[store]
manifest_url = "https://raw.githubusercontent.com/.../manifest.json"
```

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────┐
│           A.T.L.A.S (UI)                │
│  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │  Brain   │  │  Router  │  │  UI    │ │
│  │  (Groq)  │  │          │  │(Textual)│ │
│  └──────────┘  └──────────┘  └────────┘ │
└────────────────┬────────────────────────┘
                 │
        ┌────────▼────────┐
        │  Agent Manager  │
        └────────┬────────┘
                 │ (sockets UNIX)
    ┌────────────┼────────────┐
    ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐
│T.I.T.A.N│ │Agente 2│  │Agente N│
└────────┘  └────────┘  └────────┘
```

- **Brain**: Interpreta la intención del usuario con Groq
- **Router**: Decide si es chat o acción, y a qué categoría pertenece
- **Agent Manager**: Lanza agentes como procesos independientes
- **Agentes**: Se comunican con A.T.L.A.S mediante sockets UNIX efímeros

---

## 🗺️ Roadmap

- [ ] Más agentes especializados (análisis de datos, desarrollo, automatización)
- [ ] Sistema de actualizaciones automáticas de agentes
- [ ] Soporte para Linux y Windows
- [ ] Agentes con memoria persistente
- [ ] Marketplace público de agentes
- [ ] Plugins para editores de código

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

---

## 🙏 Agradecimientos

- [Groq](https://groq.com/) por su API ultrarrápida de LLM
- [Textual](https://textual.textualize.io/) por el framework de TUI
- La comunidad de macOS por AppleScript

---

**¿Te gusta el proyecto?** ¡Dale una ⭐ y contribuye con tus propios agentes!
