import os
env = os.environ.get("DJANGO_ENV", "development")
if env == "production":
    from .production import *  # noqa
else:
    from .development import *  # noqa
