#!/bin/bash

# 1. Initialize the repository
git init

# 2. Create a professional .gitignore
# This prevents uploading your virtual environment and local test results
cat <<EOF > .gitignore
venv/
__pycache__/
.streamlit/
*.csv
*.png
*.pyc
.DS_Store
EOF

# 3. Create a basic requirements file
cat <<EOF > requirements.txt
streamlit
requests
psutil
pandas
gputil
plotly
EOF

# 4. Create a starter README
cat <<EOF > README.md
# Olla-Metrics Pro
A modular performance benchmarking dashboard for local LLMs using Ollama.

## Features
- Real-time TPS (Tokens Per Second) tracking.
- Peak resource monitoring (CPU, GPU, VRAM, RAM) using concurrent threading.
- Interactive Plotly visualizations.
- Modular Python architecture for easy expansion.

## Setup
1. Install requirements: \`pip install -r requirements.txt\`
2. Run the app: \`streamlit run app.py\`
EOF

# 5. Add files and make the first commit
git add .
git commit -m "Initial commit: Modular LLM benchmarking dashboard"

echo "-------------------------------------------------------"
echo "Local repository initialized and first commit created!"
echo "Next steps:"
echo "1. Create a NEW repo on GitHub named 'ollama-bench'"
echo "2. Copy the URL (https://github.com/your-user/ollama-bench.git)"
echo "3. Run these two commands:"
echo "   git remote add origin YOUR_URL_HERE"
echo "   git push -u origin main"
echo "-------------------------------------------------------"
