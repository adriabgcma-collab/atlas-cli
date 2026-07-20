# atlas/ui/app.py
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Input, RichLog, Static, Markdown
from textual.binding import Binding
from dotenv import load_dotenv
import pyperclip
import os
import asyncio

from atlas.core.logger import AtlasLogger
from atlas.core.brain import AtlasBrain
from atlas.core.config_manager import ConfigManager
from atlas.core.agent_manager import AgentManager
from atlas.core.agent_store import AgentStore

class AtlasApp(App):
    """A.T.L.A.S - Automated Task Lifecycle & Agent Supervisor"""
    
    CSS = """
    Screen { layout: vertical; }
    #status-bar { dock: top; height: 1; background: $primary-darken-2; color: $text; padding: 0 1; text-style: bold; }
    #main-container { height: 1fr; }
    #chat-panel { width: 2fr; border-right: solid $primary-darken-1; padding: 1; }
    #log-panel { width: 1fr; background: $surface-darken-1; padding: 1; }
    #input-box { dock: bottom; height: 3; margin: 1; }
    .user-message { color: $success; padding: 1 0; text-style: bold; }
    .system-message { color: $warning; padding: 1 0; text-style: italic; }
    .command-message { color: $accent; padding: 1 0; }
    Markdown { background: transparent; padding: 0 0 1 0; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Salir"),
        Binding("ctrl+l", "copy_logs", "Copiar Logs"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("A.T.L.A.S | Estado: Iniciando...", id="status-bar")
        with Horizontal(id="main-container"):
            yield VerticalScroll(id="chat-panel")
            yield RichLog(id="log-panel", wrap=True)
        yield Input(placeholder="Escribe un comando para A.T.L.A.S...", id="input-box")

    def on_mount(self) -> None:
        log_panel = self.query_one("#log-panel", RichLog)
        self.logger = AtlasLogger(log_panel, retention_days=7)
        self.chat_panel = self.query_one("#chat-panel", VerticalScroll)
        
        # Estados del sistema (inicializados a None para evitar AttributeError)
        self.history = []
        self.pending_confirmation = None
        self.setup_state = None
        self.pending_dependencies = None
        self.store_catalog = []
        self.brain = None
        self.config = None
        self.agent_manager = None
        self.store = None
        self.categories = []
        
        self.update_status("Sistema", "Iniciando")
        
        # Comprobar configuración inicial
        if not os.path.exists(".env"):
            self.logger.info("setup", "Primera ejecución detectada. Iniciando asistente...")
            self._start_setup_wizard()
        else:
            self._initialize_core()

    def _start_setup_wizard(self):
        """Inicia el asistente de configuración inicial"""
        self.setup_state = "api_key"
        self.chat_panel.mount(Markdown("### ⚙️ Asistente de Configuración Inicial\nBienvenido a A.T.L.A.S. Para comenzar, necesito tu **API Key de Groq**.\nPor favor, pégala aquí:"))
        self.update_status("Setup", "Esperando API Key")

    def _initialize_core(self):
        """Inicializa el cerebro y la tienda si ya hay config"""
        try:
            self.brain = AtlasBrain(max_history=8)
            self.config = ConfigManager()
            self.agent_manager = AgentManager(self.logger)
            self.store = AgentStore()
            self.categories = self.config.get_categories()
            
            # Si no hay agentes instalados, forzar tienda
            if not self.config.get_enabled_agents():
                self.logger.info("setup", "No hay agentes. Abriendo tienda...")
                self._open_store()
            else:
                self.logger.info("init", f"Sistema inicializado. Categorías: {self.categories}")
                self.update_status("A.T.L.A.S", "Esperando")
        except Exception as e:
            self.logger.error("init", f"Error: {str(e)}")
            self.chat_panel.mount(Static(f"[bold red]Error crítico: {str(e)}[/bold red]", markup=True))

    def _open_store(self):
        """Abre el menú de la tienda"""
        self.setup_state = "store_browsing"
        self.chat_panel.mount(Markdown("### 🛒 Tienda de Agentes\nCargando catálogo desde GitHub..."))
        self.update_status("Tienda", "Cargando...")
        
        # Lanzar la carga en segundo plano
        asyncio.create_task(self._fetch_and_display_store())

    async def _fetch_and_display_store(self):
        """Descarga el manifiesto y muestra las opciones"""
        try:
            manifest = await self.store.fetch_manifest()
            if not manifest:
                self.chat_panel.mount(Static("[bold red]Error: No se pudo cargar el catálogo de agentes.[/bold red]", markup=True))
                self.update_status("Tienda", "Error")
                return

            agent_list = "\n".join([f"**{i+1}. {a['name']}** ({a['category']}) - {a.get('description', 'Sin descripción')}" for i, a in enumerate(manifest)])
            prompt = f"Agentes disponibles:\n{agent_list}\n\nEscribe el **número** del agente que quieres instalar (o `/salir` para cancelar):"
            self.chat_panel.mount(Markdown(prompt))
            self.store_catalog = manifest
            self.update_status("Tienda", "Esperando selección")
        except Exception as e:
            self.chat_panel.mount(Static(f"[bold red]Error en tienda: {e}[/bold red]", markup=True))

    def update_status(self, agent_name: str, state: str) -> None:
        self.query_one("#status-bar", Static).update(f"A.T.L.A.S | {agent_name} | Estado: {state}")

    def _parse_user_choice(self, user_input: str, agents_dict: dict) -> str:
        choice = user_input.strip().lower()
        agent_keys = list(agents_dict.keys())
        if choice in ["el más óptimo", "optimo", "el que quieras", "tu eliges", "default"]: 
            return agent_keys[0]
        if choice.isdigit() and 1 <= int(choice) <= len(agent_keys): 
            return agent_keys[int(choice) - 1]
        for key in agent_keys:
            if key.replace("_", "").lower() == choice or key.replace(".", "").lower() == choice: 
                return key
        return None

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_message = event.value
        if not user_message.strip():
            return

        self.chat_panel.mount(Static(f"[bold green]Tú:[/bold green] {user_message}", classes="user-message", markup=True))
        event.input.clear()
        self.chat_panel.scroll_end(animate=False)

        # 1. FLUJO DE SETUP / TIENDA
        if self.setup_state:
            await self._handle_setup_input(user_message)
            return

        # 2. COMANDOS NATIVOS
        if self._handle_native_commands(user_message):
            return

        # 3. ZONA GRIS
        if self.pending_confirmation:
            self._handle_gray_zone_input(user_message)
            return

        # 4. FLUJO NORMAL
        await self._handle_normal_chat(user_message)

    async def _handle_setup_input(self, user_message: str):
        if user_message.lower() == '/salir' and self.setup_state == 'store_browsing':
            self.setup_state = None
            self.chat_panel.mount(Static("[dim]Instalación cancelada.[/dim]", markup=True))
            return

        if self.setup_state == "api_key":
            api_key = user_message.strip()
            if not api_key.startswith("gsk_"):
                self.chat_panel.mount(Static("[bold red]❌ API Key no válida. Debe empezar por 'gsk_'. Inténtalo de nuevo:[/bold red]", markup=True))
                return
            
            with open(".env", "w") as f:
                f.write(f"GROQ_API_KEY={api_key}\n")
            
            # Recargar las variables de entorno para que el cerebro las lea
            load_dotenv(override=True)
            
            self.logger.info("setup", "API Key guardada en .env")
            self.chat_panel.mount(Static("[bold green]✅ API Key validada y guardada.[/bold green]", markup=True))
            
            self.setup_state = None
            self._initialize_core()
            
        elif self.setup_state == "store_browsing":
            if user_message.isdigit() and 1 <= int(user_message) <= len(self.store_catalog):
                selected_agent = self.store_catalog[int(user_message) - 1]
                self.chat_panel.mount(Markdown(f"⏳ Instalando **{selected_agent['name']}**..."))
                self.update_status("Tienda", "Instalando...")
                
                result = self.store.install_agent(selected_agent)
                
                if result["success"]:
                    self.chat_panel.mount(Static(f"[bold green]✅ Agente descargado e instalado.[/bold green]", markup=True))
                    if result["dependencies"]:
                        self.setup_state = "dependency_confirm"
                        self.pending_dependencies = result["dependencies"]
                        deps_str = ", ".join(result["dependencies"])
                        self.chat_panel.mount(Markdown(f"⚠️ Este agente requiere: **{deps_str}**.\n¿Instalo las dependencias? (escribe **si** o **no**)"))
                        self.update_status("Tienda", "Esperando confirmación")
                    else:
                        self.chat_panel.mount(Static("[bold green]🎉 ¡Configuración completada! Reiniciando núcleo...[/bold green]", markup=True))
                        self.setup_state = None
                        self._initialize_core()
                else:
                    self.chat_panel.mount(Static(f"[bold red]❌ Error: {result['error']}[/bold red]", markup=True))
                    self.setup_state = None
            else:
                self.chat_panel.mount(Static("[bold yellow]Opción no válida. Escribe el número del agente.[/bold yellow]", markup=True))
                
        elif self.setup_state == "dependency_confirm":
            if user_message.lower() in ["si", "sí", "yes", "y"]:
                self.chat_panel.mount(Markdown("⚙️ Instalando dependencias con pip..."))
                result = self.store.install_dependencies(self.pending_dependencies)
                if result["success"]:
                    self.chat_panel.mount(Static(f"[bold green]✅ {result['message']}[/bold green]", markup=True))
                else:
                    self.chat_panel.mount(Static(f"[bold red]❌ {result['error']}[/bold red]", markup=True))
            else:
                self.chat_panel.mount(Static("[dim]Dependencias no instaladas. El agente podría fallar.[/dim]", markup=True))
            
            self.setup_state = None
            self.pending_dependencies = None
            self.chat_panel.mount(Static("[bold green]🎉 ¡Configuración completada! Reiniciando núcleo...[/bold green]", markup=True))
            self._initialize_core()

    def _handle_native_commands(self, command: str) -> bool:
        if not command.startswith('/'): 
            return False
        cmd = command.strip().lower()
        
        if cmd == '/clear':
            for widget in self.chat_panel.children: 
                widget.remove()
            self.history = []
            return True
        elif cmd == '/cancelar':
            if self.pending_confirmation:
                self.pending_confirmation = None
                self.chat_panel.mount(Static("[bold yellow]⚠️ Acción cancelada.[/bold yellow]", markup=True))
                self.update_status("A.T.L.A.S", "Esperando")
            return True
        elif cmd == '/tienda':
            self._open_store()
            return True
        elif cmd == '/ayuda':
            help_text = "**Comandos:**\n- `/clear`: Borra chat.\n- `/cancelar`: Aborta acción.\n- `/tienda`: Abre tienda.\n- `/ayuda`: Muestra ayuda."
            self.chat_panel.mount(Markdown(help_text))
            return True
        else:
            self.chat_panel.mount(Static(f"[bold red]Comando desconocido: {command}[/bold red]", markup=True))
            return True

    def _handle_gray_zone_input(self, user_message: str):
        self.logger.info("zona_gris", f"Procesando elección: {user_message}")
        selected_key = self._parse_user_choice(user_message, self.pending_confirmation["agents"])
        
        if selected_key:
            agent_name = selected_key
            agent_config = self.pending_confirmation["agents"][selected_key]
            query = self.pending_confirmation["query"]
            
            self.pending_confirmation = None
            self.update_status(agent_name.upper().replace("_", "."), "Ejecutando")
            
            response_widget = Markdown(f"**{agent_name.upper().replace('_', '.')}:** ")
            self.chat_panel.mount(response_widget)
            
            asyncio.create_task(self._execute_agent_async(agent_name, agent_config, query, response_widget))
        else:
            self.chat_panel.mount(Static(f"[bold yellow]Opción no válida. Elige número, nombre o 'el más óptimo'.[/bold yellow]", markup=True))

    async def _execute_agent_async(self, agent_name, agent_config, query, response_widget):
        full_response = await self.agent_manager.execute(agent_name, agent_config, query)
        response_widget.update(f"**{agent_name.upper().replace('_', '.')}:** {full_response}")
        self.logger.info("agent_manager", f"Output final: {full_response}")
        self.history.append({"role": "assistant", "content": full_response})
        self.update_status(agent_name.upper().replace("_", "."), "Esperando")

    async def _handle_normal_chat(self, user_message: str):
        if not self.brain:
            self.chat_panel.mount(Static("[bold red]Error: Cerebro no inicializado.[/bold red]", markup=True))
            return

        self.update_status("A.T.L.A.S", "Analizando")
        self.logger.info("atlas", f"Mensaje recibido: {user_message}")
        self.history.append({"role": "user", "content": user_message})

        try:
            route_result = await self.brain.route_message(user_message, self.categories)
            
            if route_result["type"] == "chat":
                self.update_status("A.T.L.A.S", "Generando")
                response_widget = Markdown("**A.T.L.A.S:** ")
                self.chat_panel.mount(response_widget)
                
                full_response = ""
                async for token in self.brain.think_stream(user_message, self.history[:-1]):
                    full_response += token
                    response_widget.update(f"**A.T.L.A.S:** {full_response}")
                    self.chat_panel.scroll_end(animate=False)
                    
                self.logger.info("brain", f"Output final: {full_response}")
                self.history.append({"role": "assistant", "content": full_response})
                self.update_status("A.T.L.A.S", "Esperando")
                
            elif route_result["type"] == "action":
                category = route_result["category"]
                query = route_result["query"]
                available_agents = self.config.get_agents_by_category(category)
                
                if not available_agents:
                    self.chat_panel.mount(Static(f"[bold red]No hay agentes para: {category}[/bold red]", markup=True))
                    self.update_status("A.T.L.A.S", "Esperando")
                    return

                self.pending_confirmation = {
                    "category": category, "query": query, "agents": available_agents
                }
                
                agent_list_str = ", ".join([f"{i+1}. {name.upper().replace('_', '.')}" for i, name in enumerate(available_agents.keys())])
                prompt_msg = f"[bold yellow]⚠️ Acción de '{category}' detectada.[/bold yellow]\nAgentes: {agent_list_str}.\n¿Cuál prefieres? (número, nombre o 'el más óptimo')"
                self.chat_panel.mount(Static(prompt_msg, classes="system-message", markup=True))
                self.update_status("Zona Gris", "Esperando confirmación")

        except Exception as e:
            self.logger.error("router", f"Error: {str(e)}")
            self.chat_panel.mount(Static(f"[bold red]Error: {str(e)}[/bold red]", markup=True))
            self.update_status("A.T.L.A.S", "Error")

    def action_copy_logs(self) -> None:
        log_panel = self.query_one("#log-panel", RichLog)
        log_text = "\n".join([line.text for line in log_panel.lines])
        pyperclip.copy(log_text)
        self.notify("📋 Logs copiados", timeout=2)

    def on_close(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.close()