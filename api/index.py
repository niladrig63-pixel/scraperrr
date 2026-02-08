"""
api/index.py — Vercel serverless entry point.

Re-exports the FastAPI app from the project root so Vercel's
@vercel/python runtime can discover it.
"""
import sys
import os

# Add the project root to the Python path so imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
