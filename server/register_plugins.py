import sys

sys.path.append(".")

from server.entities.plugin_manager import register_plugins
from server.db import check_database_version, migrate_database


# Register plugins
print("[thethe_server]: Registering plugins")
register_plugins()


# Check and update database scheme
print("[thethe_server]: Check if database needs migration")
needs = check_database_version()
if not needs:
    print("[thethe_server]: Database looks good, continuing")
else:
    print("[thethe_server]: Your database is old, migrating")
    migrate_database()
