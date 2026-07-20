#!/bin/bash

# ============================================
# Instalador de A.T.L.A.S
# Asistente de Terminal Inteligente para macOS
# ============================================

set -e  # Detener si hay error

echo "🏛️  Instalando A.T.L.A.S..."
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Detectar la ruta del proyecto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}📁 Ruta del proyecto: $PROJECT_DIR${NC}"

# Verificar que estamos en macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}❌ Error: A.T.L.A.S solo funciona en macOS actualmente${NC}"
    exit 1
fi

# Verificar que Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: Python 3 no está instalado${NC}"
    echo "Instala Python desde: https://www.python.org/downloads/"
    exit 1
fi

echo -e "${GREEN}✅ Python 3 detectado${NC}"

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
    echo -e "${GREEN}✅ Entorno virtual creado${NC}"
else
    echo -e "${GREEN}✅ Entorno virtual ya existe${NC}"
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "📦 Instalando dependencias..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo -e "${GREEN}✅ Dependencias instaladas${NC}"

# Crear el script de inicio en /usr/local/bin
echo "🔗 Creando comando 'atlas'..."

# Verificar si /usr/local/bin existe
if [ ! -d "/usr/local/bin" ]; then
    sudo mkdir -p /usr/local/bin
fi

# Crear el script
sudo tee /usr/local/bin/atlas > /dev/null <<EOF
#!/bin/bash

# Script de inicio de A.T.L.A.S
ATLAS_DIR="$PROJECT_DIR"

if [ ! -d "\$ATLAS_DIR" ]; then
    echo "❌ Error: No se encuentra A.T.L.A.S en \$ATLAS_DIR"
    exit 1
fi

if [ ! -d "\$ATLAS_DIR/venv" ]; then
    echo "❌ Error: No se encuentra el entorno virtual"
    exit 1
fi

cd "\$ATLAS_DIR" || exit 1
source venv/bin/activate
python -m atlas.main "\$@"
EOF

# Dar permisos de ejecución
sudo chmod +x /usr/local/bin/atlas

echo -e "${GREEN}✅ Comando 'atlas' creado${NC}"

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}🎉 ¡A.T.L.A.S instalado correctamente!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Ahora puedes ejecutar A.T.L.A.S desde cualquier carpeta:"
echo ""
echo -e "${BLUE}  atlas${NC}"
echo ""
echo "En la primera ejecución, A.T.L.A.S te guiará para configurar tu API Key de Groq."
echo ""