"""Entry point for cPanel / Phusion Passenger.

cPanel's "Setup Python App" starts the application from this file and looks for
a WSGI callable named `application`. Environment variables set in the cPanel UI
are already present here, so nothing secret lives in this file.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_ENV", "production")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
