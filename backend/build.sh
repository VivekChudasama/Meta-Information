#!/usr/bin/env bash
# Render build script — install CPU-only PyTorch first to avoid
# pulling in the massive CUDA build that exceeds memory limits.

set -o errexit

pip install --upgrade pip

# Install CPU-only PyTorch BEFORE docling so it doesn't pull CUDA wheels
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Now install the rest of the requirements
pip install -r requirements.txt

# Download required NLTK data for sumy
python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True)"
