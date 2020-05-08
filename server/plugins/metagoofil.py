import os
import traceback
from urllib.parse import urlparse

import tasks.deps.metagoofil.metagoofil as _metagoofil

from server.entities.plugin_manager import PluginManager
from server.entities.resource_types import ResourceType
from tasks.tasks import celery_app
from server.entities.plugin_result_types import PluginResultStatus

# Which resources are this plugin able to work with
RESOURCE_TARGET = [ResourceType.DOMAIN]

# Plugin Metadata {a decription, if target is actively reached and name}
PLUGIN_AUTOSTART = False
PLUGIN_DESCRIPTION = (
    "Information gathering tool for extracting metadata of public documents"
)
PLUGIN_DISABLE = False
PLUGIN_IS_ACTIVE = False
PLUGIN_NAME = "metagoofil"
PLUGIN_NEEDS_API_KEY = False

API_KEY = False
API_KEY_IN_DDBB = bool(API_KEY)
API_KEY_DOC = ""
API_KEY_NAMES = []


class Plugin:
    def __init__(self, resource, project_id):
        self.project_id = project_id
        self.resource = resource

    def do(self):
        resource_type = self.resource.get_type()

        try:
            to_task = {
                "domain": self.resource.get_data()["canonical_name"],
                "resource_id": self.resource.get_id_as_string(),
                "project_id": self.project_id,
                "resource_type": resource_type.value,
                "plugin_name": PLUGIN_NAME,
            }
            metagoofil.delay(**to_task)

        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))


@celery_app.task
def metagoofil(domain, plugin_name, project_id, resource_id, resource_type):
    try:
        result_status = PluginResultStatus.STARTED
        print("Analizing {} with metagoofil".format(domain))

        response = _metagoofil._main(domain)

        if response:
            result_status = PluginResultStatus.COMPLETED
        else:
            result_status = PluginResultStatus.RETURN_NONE

        PluginManager.set_plugin_results(
            resource_id, plugin_name, project_id, response, result_status
        )

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return None
