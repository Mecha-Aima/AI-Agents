#!/usr/bin/env python3
"""
Launcher script for the Dev Tools Research Assistant Streamlit app.
This script ensures the correct Python interpreter from the uv virtual environment is used.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Get the project root directory (parent of dev-research-agent)
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    venv_python = project_root / ".venv" / "bin" / "python"
    
    # Check if the virtual environment exists
    if not venv_python.exists():
        print("❌ Virtual environment not found!")
        print(f"Expected path: {venv_python}")
        print("Please ensure you have run 'uv sync' in the project root.")
        sys.exit(1)
    
    # Set the Python path for Streamlit
    os.environ["STREAMLIT_SERVER_PYTHON_PATH"] = str(venv_python)
    
    # Run the Streamlit app
    print("🚀 Starting Dev Tools Research Assistant...")
    print(f"Using Python: {venv_python}")
    
    try:
        subprocess.run([
            str(venv_python), "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ], cwd=current_dir)
    except KeyboardInterrupt:
        print("\n👋 App stopped by user")
    except Exception as e:
        print(f"❌ Error starting app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 