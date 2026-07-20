# atlas/core/logger.py
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from textual.widgets import RichLog

class AtlasLogger:
    """Sistema de logs en formato JSON para A.T.L.A.S"""
    
    def __init__(self, log_panel: RichLog, retention_days: int = 7):
        self.log_panel = log_panel
        self.retention_days = retention_days
        
        # Crear carpeta de logs si no existe
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Limpieza de logs antiguos
        self._clean_old_logs()
        
        # Archivo de log con fecha
        log_file = self.log_dir / f"atlas_{datetime.now().strftime('%Y%m%d')}.log"
        self.log_file = open(log_file, "a", encoding="utf-8")

    def _clean_old_logs(self):
        """Elimina archivos de log con más de X días de antigüedad"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_count = 0
        
        for log_file in self.log_dir.glob("*.log"):
            # Comprobar la fecha de modificación
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                log_file.unlink() # Borrar archivo
                deleted_count += 1
                
        if deleted_count > 0:
            # Lo registramos en la consola del sistema (stderr) para no interferir con la UI aún
            print(f"[Logger] Se han eliminado {deleted_count} archivos de log antiguos.")

    def _write_log(self, level: str, module: str, message: str):
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "level": level,
            "module": module,
            "message": message
        }
        log_json = json.dumps(log_entry, ensure_ascii=False)
        self.log_panel.write(log_json)
        self.log_file.write(log_json + "\n")
        self.log_file.flush()

    def info(self, module: str, message: str):
        self._write_log("INFO", module, message)

    def warning(self, module: str, message: str):
        self._write_log("WARNING", module, message)

    def error(self, module: str, message: str):
        self._write_log("ERROR", module, message)
    
    def close(self):
        if hasattr(self, 'log_file'):
            self.log_file.close()