#!/bin/bash
# Quick activation script for kb-gen

echo "🔧 Activating kb-gen environment..."
source venv/bin/activate

echo "✅ Virtual environment activated"
echo ""
echo "📚 Available commands:"
echo "  kb-gen scan ./CleanArchitecture"
echo "  kb-gen update ./CleanArchitecture"
echo "  kb-gen impact ./CleanArchitecture --files src/Core/Entity.cs"
echo "  kb-gen impact ./CleanArchitecture --git-diff"
echo ""
echo "💡 Type 'kb-gen --help' for more options"
echo ""

# Keep the shell open with venv activated
exec $SHELL
