import json
import traceback

import requests

import dns.message
import dns.query
import dns.rdatatype

from server.entities.plugin_manager import PluginManager
from server.entities.resource_types import ResourceType
from tasks.tasks import celery_app
from server.entities.plugin_result_types import PluginResultStatus


# Which resources are this plugin able to work with
RESOURCE_TARGET = [ResourceType.DOMAIN]

# Plugin Metadata {a description, if target is actively reached and name}
PLUGIN_AUTOSTART = True
PLUGIN_DESCRIPTION = "Check if a domain is malicious in on our DNS-over-HTTPS server"
PLUGIN_DISABLE = False
PLUGIN_IS_ACTIVE = False
PLUGIN_NAME = "doh"
PLUGIN_NEEDS_API_KEY = False

API_KEY = False
API_KEY_IN_DDBB = False
API_KEY_DOC = ""
API_KEY_NAMES = []

DOH_SERVER = "https://doh-beta.e-paths.com"
MALICIOUS_RESPONSE = "18.194.105.161"


class Plugin:
    def __init__(self, resource, project_id):
        self.project_id = project_id
        self.resource = resource

    def do(self):
        resource_type = self.resource.get_type()

        try:
            if resource_type == ResourceType.DOMAIN:
                to_task = {
                    "domain": self.resource.get_data()["domain"],
                    "resource_id": self.resource.get_id_as_string(),
                    "project_id": self.project_id,
                    "resource_type": resource_type.value,
                    "plugin_name": PLUGIN_NAME,
                }
                doh.delay(**to_task)

        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))


@celery_app.task
def doh(plugin_name, project_id, resource_id, resource_type, domain):
    try:
        results = {}
        result_status = PluginResultStatus.STARTED

        with requests.sessions.Session() as session:
            q = dns.message.make_query(domain, dns.rdatatype.A)
            r = dns.query.https(q, DOH_SERVER, session=session)
            if r.answer:
                for answer in r.answer:
                    a = answer.to_text()
                    if a.split(" ")[4] == MALICIOUS_RESPONSE:
                        results["malicious"] = True
                    else:
                        results["malicious"] = False
                    result_status = PluginResultStatus.COMPLETED
            else:
                result_status = PluginResultStatus.RETURN_NONE

        PluginManager.set_plugin_results(
            resource_id, plugin_name, project_id, results, result_status
        )
    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
