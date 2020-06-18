"""
This is a plugin made for the platform TheTHE (The Threat Hunting Environment)
that consumes the Dinoflux API.

This source code will also be available on https://github.com/santiagorocha/thetheplugin

Author: Santiago Rocha.
Github: https://github.com/santiagorocha
Twitter: https://twitter.com/sarvmetal
Linkedin: https://www.linkedin.com/in/santiago-rocha-62b38762/
"""
import requests
import json
import traceback

from tasks.tasks import celery_app
from server.entities.resource_types import ResourceType
from server.entities.plugin_result_types import PluginResultStatus
from server.entities.plugin_manager import PluginManager

from tasks.api_keys import KeyRing

URL_API = "https://www.dinoflux.com/api/analyses/search"

# This URL is used to query a complete dinoflux analysis report
URL_REPORT = "https://www.dinoflux.com/private/intelligence/report/"

API_KEY = KeyRing().get("dinoflux")
API_KEY_IN_DDBB = bool(API_KEY)
API_KEY_DOC = "https://www.dinoflux.com/private/intelligence/search/"
API_KEY_NAMES = ["dinoflux"]

PLUGIN_NAME = "dinoflux"
PLUGIN_DESCRIPTION = "Search dinoflux reports from a binary hash, IPv4, URL or Filename"

PLUGIN_IS_ACTIVE = False
PLUGIN_AUTOSTART = False
PLUGIN_DISABLE = False
PLUGIN_NEEDS_API_KEY = True

RESOURCE_TARGET = [
    ResourceType.HASH,
    ResourceType.IPv4,
    ResourceType.URL,
    ResourceType.FILE,
    ResourceType.DOMAIN,
]


class Plugin:
    def __init__(self, resource, project_id):
        self.project_id = project_id
        self.resource = resource

    def do(self):
        resource_type = self.resource.get_type()

        try:
            to_task = {
                "target": self.resource.get_data()["canonical_name"],
                "resource_id": self.resource.get_id_as_string(),
                "project_id": self.project_id,
                "resource_type": resource_type.value,
                "plugin_name": PLUGIN_NAME,
            }
            dinoflux.delay(**to_task)

        except Exception as e:
            tb1 = traceback.TracebackException.from_exception(e)
            print("".join(tb1.format()))


@celery_app.task
def dinoflux(plugin_name, project_id, resource_id, resource_type, target):
    try:
        query_result = None

        API_KEY = KeyRing().get(PLUGIN_NAME)
        if not API_KEY:
            print("No API key...!")
            result_status = PluginResultStatus.NO_API_KEY
        else:
            result_status = PluginResultStatus.STARTED
            resource_type = ResourceType(resource_type)

            if resource_type:
                query_result = get_report(resource_type, target)
            else:
                print("No resource type")

        if query_result:
            result_status = PluginResultStatus.COMPLETED
        else:
            result_status = PluginResultStatus.RETURN_NONE

        PluginManager.set_plugin_results(
            resource_id, plugin_name, project_id, query_result, result_status
        )

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))


"""
Dinoflux API returns all reports that are related to an IOC, these IOCs could
be Hashes, IPs, URLs, Filenames, among others.

Since an IOC could return several reports and those reports are separated
in different pages (10 reports per page and API query), is necessary to
query all pages and save them in a single one and then return it as a
result to thethe. If there are several pages, it could take a little while
all requests are performed and saved.
"""


def get_report(resource_type, target):
    dinoflux_res = None
    all_reports = {}
    reports = []

    if resource_type == ResourceType.HASH:
        hash_type = get_hash_type(target)
        if hash_type is not None:
            query = hash_type + ":" + target
            dinoflux_res = send_query(query)
    elif resource_type == ResourceType.IPv4:
        query = "ip:" + target
        dinoflux_res = send_query(query)
    elif resource_type == ResourceType.URL:
        query = "http.url:" + target
        dinoflux_res = send_query(query)
    elif resource_type == ResourceType.FILE:
        query = "file:" + target
        dinoflux_res = send_query(query)
    elif resource_type == ResourceType.DOMAIN:
        query = "host:" + target
        dinoflux_res = send_query(query)
    else:
        print(f"[{PLUGIN_NAME}]: Resource type does not found")

    if dinoflux_res:
        dinoflux_json = json.loads(dinoflux_res.content)
        total_reports = dinoflux_json.get("total")
        if total_reports > 10:
            reports = get_reports(total_reports, query)
        else:
            analyses = dinoflux_json.get("analyses")
            for analysis in analyses:
                reports.append(get_clean_report(analysis))

        all_reports["analyses"] = reports

        print(all_reports)
        return all_reports
    else:
        return None


"""
This function performs a query request, by default it requests only the first
page if there are less or even 10 reports available for a single IOC
"""


def send_query(query, page=1):
    params = {"key": API_KEY, "query": query, "page": page}

    dinoflux_res = requests.get(URL_API, params=params)

    if dinoflux_res.status_code != 200:
        return None
    else:
        return dinoflux_res


"""
This function is in charge of determine the quantity of pages to request, make
the request, save them all in a list and return them. If any of the requests
to the dinoflux API fails, it will stop and return the collected information until
the moment of fail.
"""


def get_reports(total_reports, query):
    reports = []

    if total_reports % 10 == 0:
        pages = total_reports / 10
    else:
        pages = total_reports // 10 + 1

    current_page = 1
    while current_page <= pages:
        dinoflux_res = send_query(query, current_page)
        if dinoflux_res:
            dinoflux_json = json.loads(dinoflux_res.content)
            analyses = dinoflux_json.get("analyses")
            for analysis in analyses:
                reports.append(get_clean_report(analysis))
            current_page += 1
        else:
            break

    return reports


"""
This function is in charge of determine the type of hash based on
lenght of the hash.
"""


def get_hash_type(hash):
    hash_len = len(hash)
    hash_type = None
    if hash_len == 32:
        hash_type = "md5"
    elif hash_len == 40:
        hash_type = "sha1"
    elif hash_len == 64:
        hash_type = "sha256"

    return hash_type


"""
By default, dinoflux returns too many valuable information from a report,
these fields are (it's important to notice that the all fields are not present in
all reports):

network: Gives a number of network observables
timestamp: A timestamp of the analysis
sandbox: A sample score determined by dinoflux and signatures, each signature
has a description of the of the sample's behavior in the infected machine, the
severity and the name of the signature.
static: Information about the pattern matching with yara
threat: The threat name
date: When the sample was uploaded to dinoflux
hashes: Mutiple hashes identifiers (sha256, sha1, imphash and md5)
similar: similar samples in the dinoflux database
id: An unique Dinoflux ID indetifier, I used this to build the URL where the
report is located


The next functions parses each report and get the information that, from my point
of view, could be important to show to the final user in thethe. If the user wants
to get a complete report, will be able to consult it in the report URL.

In comments are the fields that I think are not relevant in a first view. If you want
to add any, just uncomment them.
"""


def get_clean_report(analysis):
    clean_report = {}

    network = analysis.get("network")
    timestamp = analysis.get("timestamp")
    sandbox = analysis.get("sandbox")
    # static = analysis.get("static")
    threat = analysis.get("threat")
    # date = analysis.get("date")
    hashes = analysis.get("hashes")
    # similar = analysis.get("similar")
    url_report = URL_REPORT + analysis.get("id") + "a"
    clean_report = {
        "network": network,
        "timestamp": timestamp,
        "sandbox": sandbox,
        # "static":static,
        "threat": threat,
        # "date":date,
        "hashes": hashes,
        # "similar":similar,
        "url_report": url_report,
    }

    return clean_report
