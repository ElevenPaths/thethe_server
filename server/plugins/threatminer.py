import json
import traceback

from server.entities.plugin_manager import PluginManager
from server.entities.resource_types import ResourceType
from server.entities.resource_manager import ResourceManager
from server.entities.plugin_result_types import PluginResultStatus

from tasks.tasks import celery_app
import json
import requests


# Which resources are this plugin able to work with
RESOURCE_TARGET = [ResourceType.DOMAIN, ResourceType.IPv4, ResourceType.HASH]

# Plugin Metadata {a description, if target is actively reached and name}
PLUGIN_AUTOSTART = False
PLUGIN_DESCRIPTION = "Search ThreatMiner for domain, IP or hashes"
PLUGIN_DISABLE = False
PLUGIN_IS_ACTIVE = False
PLUGIN_NAME = "threatminer"
PLUGIN_NEEDS_API_KEY = False

# IMPORTANT NOTE: Please note that the rate limit is set to 10 queries per minute.
API_KEY = False
API_KEY_IN_DDBB = False
API_KEY_DOC = ""
API_KEY_NAMES = []


class Plugin:
    def __init__(self, resource, project_id):
        self.project_id = project_id
        self.resource = resource

    def do(self):
        resource_type = self.resource.get_type()
        target = self.resource.get_data()["canonical_name"]

        if resource_type == ResourceType.HASH:
            target = self.resource.get_data()["hash"]

        try:
            to_task = {
                "target": target,
                "resource_id": self.resource.get_id_as_string(),
                "project_id": self.project_id,
                "resource_type": resource_type.value,
                "plugin_name": PLUGIN_NAME,
            }
            threatminer_task.delay(**to_task)

        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))


def threatminer_searchAPTNotes(fulltext):
    try:
        URL = "https://api.threatminer.org/v2/reports.php?q={fulltext}&rt=1"
        response = {}
        response = requests.get(URL.format(**{"fulltext": fulltext}))
        if not response.status_code == 200:
            print("API key error!")
            return None
        else:
            response = json.loads(response.content)

        return response

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return None


def threatminer_APTNotesToIoCs(filename_param, year):
    try:
        URL = (
            "https://api.threatminer.org/v2/report.php?q={filename_param}&y={year}&rt=1"
        )
        response = {}

        response = requests.get(
            URL.format(**{"filename_param": filename_param, "year": year})
        )
        if not response.status_code == 200:
            print("API key error!")
            return None
        else:
            response = json.loads(response.content)

        return response

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return None


def threatminer_AVDetection(name_virus):
    try:
        URL = "	https://api.threatminer.org/v2/av.php?q={name_virus}&rt=1"
        response = {}

        response = requests.get(URL.format(**{"name_virus": name_virus}))
        if not response.status_code == 200:
            print("API key error!")
            return None
        else:
            response = json.loads(response.content)

        return response

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return None


def threatminer_ssl(hash, tab_rt):
    try:
        URL = "https://api.threatminer.org/v2/ssl.php?q={hash}&rt={tab_rt}"
        response = {}

        response = requests.get(URL.format(**{"hash": hash, "tab_rt": tab_rt}))
        if not response.status_code == 200:
            print("API key error!")
            return None
        else:
            response = json.loads(response.content)

        return response

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return None


def threatminer_samples(hash):
    try:
        response_data = {}

        for tab_rt in range(1, 8):
            URL = "https://api.threatminer.org/v2/sample.php?q="+hash+"&rt="+str(tab_rt)+""
            print(URL)

            response = requests.get(URL)
            if not response.status_code == 200:
                print("API key error!")
                return None
            else:
                response_data["type_query"] = "hash"
                if tab_rt == 1:
                    response_data["metadata"] = json.loads(response.content)
                    print(response_data["metadata"])
                elif tab_rt == 2:
                    response_data["httptraffic"] = json.loads(response.content)
                    print(response_data["httptraffic"])
                elif tab_rt == 3:
                    response_data["hosts"] = json.loads(response.content)
                    print(response_data["hosts"])
                elif tab_rt == 4:
                    response_data["mutants"] = json.loads(response.content)
                    print(response_data["mutants"])
                elif tab_rt == 5:
                    response_data["regkeys"] = json.loads(response.content)
                    print(response_data["regkeys"])
                elif tab_rt == 6:
                    response_data["avdetect"] = json.loads(response.content)
                    print(response_data["avdetect"])
                elif tab_rt == 7:
                    response_data["reporttag"] = json.loads(response.content)
                    print(response_data["reporttag"])

        return response_data

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return None


def threatminer_ip(ip):
    try:
        response_data = {}

        for tab_rt in range(1, 7):
            URL = "https://api.threatminer.org/v2/host.php?q="+ip+"&rt="+str(tab_rt)+""
            print(URL)

            response = requests.get(URL)
            if not response.status_code == 200:
                print("API key error!")
                return None
            else:
                response_data["type_query"] = "ip"
                if tab_rt == 1:
                    response_data["whois"] = json.loads(response.content)
                    print(response_data["whois"])
                elif tab_rt == 2:
                    response_data["passivedns"] = json.loads(response.content)
                    print(response_data["passivedns"])
                elif tab_rt == 3:
                    response_data["queryuri"] = json.loads(response.content)
                    print(response_data["queryuri"])
                elif tab_rt == 4:
                    response_data["samples"] = json.loads(response.content)
                    print(response_data["samples"])
                elif tab_rt == 5:
                    response_data["sslcerts"] = json.loads(response.content)
                    print(response_data["sslcerts"])
                elif tab_rt == 6:
                    response_data["reporttag"] = json.loads(response.content)
                    print(response_data["reporttag"])

        return response_data

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return None


def threatminer_domain(domain):
    try:
        response_data = {}

        for tab_rt in range(1, 7):
            URL = "https://api.threatminer.org/v2/domain.php?q="+domain+"&rt="+str(tab_rt)+""
            #print(URL)

            response = requests.get(URL)
            #print(response.content)
            if not response.status_code == 200:
                print("API key error!")
                return None
            else:
                response_data["type_query"] = "domain"
                if tab_rt == 1:
                    response_data["whois"] = json.loads(response.content)
                    #print(response_data["whois"])
                elif tab_rt == 2:
                    response_data["passivedns"] = json.loads(response.content)
                    #print(response_data["passivedns"])
                elif tab_rt == 3:
                    response_data["queryuri"] = json.loads(response.content)
                    #print(response_data["queryuri"])
                elif tab_rt == 4:
                    response_data["samples"] = json.loads(response.content)
                    #print(response_data["samples"])
                elif tab_rt == 5:
                    response_data["subdomains"] = json.loads(response.content)
                    #print(response_data["subdomains"])
                elif tab_rt == 6:
                    response_data["reporttag"] = json.loads(response.content)
                    #print(response_data["reporttag"])

        return response_data

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return None


@celery_app.task
def threatminer_task(plugin_name, project_id, resource_id, resource_type, target):

    resource_type_miner = ResourceType(resource_type)

    try:
        query_result = {}
        result_status = PluginResultStatus.STARTED

        if resource_type_miner == ResourceType.DOMAIN:
            query_result = threatminer_domain(target)
            result_status = PluginResultStatus.COMPLETED

        elif resource_type_miner == ResourceType.IPv4:
            query_result = threatminer_ip(target)
            result_status = PluginResultStatus.COMPLETED

        elif resource_type_miner == ResourceType.HASH:
            query_result = threatminer_samples(target)
            result_status = PluginResultStatus.COMPLETED

        else:
            result_status = PluginResultStatus.RETURN_NONE
            print("threatminer resource type does not found")

        PluginManager.set_plugin_results(
            resource_id, plugin_name, project_id, query_result, result_status
        )

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))