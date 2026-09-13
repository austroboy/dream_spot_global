"""Project package.

Shared hosting rarely has the build tools that `mysqlclient` needs, so fall back
to the pure-Python PyMySQL driver when it is the one that is installed. Django
only ever sees a module called `MySQLdb`, so nothing else has to change.
"""
try:
    import MySQLdb  # noqa: F401  (the C driver is present, use it)
except ImportError:  # pragma: no cover - depends on the host
    try:
        import pymysql

        pymysql.version_info = (1, 4, 6, "final", 0)   # satisfy Django's check
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
