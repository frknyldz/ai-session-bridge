#!/bin/bash
# Setup script for ai-session-bridge development

set -e

echo "🚀 Setting up ai-session-bridge development environment..."
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
    echo "❌ Error: Python 3.10+ is required (found $python_version)"
    exit 1
fi

echo "✅ Python $python_version"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet

# Install package in editable mode with dev dependencies
echo "📥 Installing ai-session-bridge with dependencies..."
pip install -e ".[dev]" --quiet

echo "✅ Package installed"
echo ""

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
if command -v pre-commit &> /dev/null; then
    pre-commit install
    echo "✅ Pre-commit hooks installed"
else
    echo "⚠️  pre-commit not found, skipping hook installation"
fi
echo ""

# Create config directory
config_dir="$HOME/.config/ai-session-bridge"
if [ ! -d "$config_dir" ]; then
    echo "📁 Creating config directory: $config_dir"
    mkdir -p "$config_dir"

    # Copy example config if it doesn't exist
    if [ ! -f "$config_dir/config.yaml" ]; then
        echo "📄 Copying example config..."
        cp examples/config.yaml "$config_dir/config.yaml"
        echo "✅ Config file created at $config_dir/config.yaml"
    fi
else
    echo "✅ Config directory already exists"
fi
echo ""

# Create cache directory
cache_dir="$HOME/.cache/ai-session-bridge"
if [ ! -d "$cache_dir" ]; then
    echo "📁 Creating cache directory: $cache_dir"
    mkdir -p "$cache_dir"
    echo "✅ Cache directory created"
else
    echo "✅ Cache directory already exists"
fi
echo ""

# Test installation
echo "🧪 Testing installation..."
if ai-session-bridge --version &> /dev/null; then
    version=$(ai-session-bridge --version)
    echo "✅ $version"
else
    echo "❌ Installation test failed"
    exit 1
fi
echo ""

# Get the absolute path to the venv binary
VENV_BIN="$(pwd)/venv/bin/ai-session-bridge"
PIPX_BIN="$HOME/.local/bin/ai-session-bridge"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ Setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 Quick Start (Development):"
echo ""
echo "1️⃣  Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2️⃣  Try listing sessions:"
echo "   ai-session-bridge list"
echo ""
echo "3️⃣  Run tests:"
echo "   pytest"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Production Installation (Optional):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "For a global installation (works without activating venv):"
echo ""
echo "   brew install pipx      # If you don't have pipx"
echo "   pipx install ."
echo ""
echo "This installs to: $PIPX_BIN"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 MCP Server Configuration:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Choose ONE of these configurations:"
echo ""
echo "📦 If you used pipx (recommended for production):"
echo ""
echo "   {"
echo "     \"mcpServers\": {"
echo "       \"ai-session-bridge\": {"
echo "         \"command\": \"$PIPX_BIN\","
echo "         \"args\": [\"serve\"]"
echo "       }"
echo "     }"
echo "   }"
echo ""
echo "🔨 If you're using venv (for development):"
echo ""
echo "   {"
echo "     \"mcpServers\": {"
echo "       \"ai-session-bridge\": {"
echo "         \"command\": \"$VENV_BIN\","
echo "         \"args\": [\"serve\"]"
echo "       }"
echo "     }"
echo "   }"
echo ""
echo "   For VS Code Copilot, use \"servers\" instead of \"mcpServers\""
echo ""
echo "📖 Documentation:"
echo "   • Quickstart: QUICKSTART.md"
echo "   • README: README.md"
echo "   • Contributing: CONTRIBUTING.md"
echo ""
