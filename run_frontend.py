#!/usr/bin/env python3
"""
OMRChecker Frontend Launcher

Simple launcher script for the Gradio-based web interface.
"""

import sys
from pathlib import Path

# Add frontend directory to path
frontend_dir = Path(__file__).parent / "frontend"
sys.path.insert(0, str(frontend_dir))

from app import create_gradio_interface

if __name__ == "__main__":
    print("=" * 60)
    print("OMRChecker - Gradio Frontend")
    print("=" * 60)
    print("\nStarting web interface...")
    print("Once started, open your browser to the URL shown below\n")

    demo = create_gradio_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        inbrowser=True,  # Automatically open browser
    )
