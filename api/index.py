"""Vercel serverless entry point.

Vercel's Python runtime looks for a WSGI/ASGI callable named `app` in this file.
Everything else is the ordinary Django project.
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_ENV", "production")

from config.wsgi import application  # noqa: E402

app = application
