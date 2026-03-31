"""
Guardian AI  —  Dashboard Entry Point
======================================
Run with:  python -m dashboard.run   (from project root)
      or:  python dashboard/run.py
"""

import sys
import os

# Ensure the project root is on sys.path so 'dashboard' is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.app import app

if __name__ == "__main__":
    print("[Guardian AI] Dashboard starting on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
