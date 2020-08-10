import traceback
import time
import json
import bson

from flask import Blueprint, request, abort, jsonify, Response

from server.utils.tokenizer import token_required
from server.entities.resource_manager import ResourceManager
from server.entities.project import Projects

search_api = Blueprint("search", __name__)


@search_api.route("/api/search", methods=["POST"])
@token_required
def search(user):
    try:
        query = request.json["query"]
        if not query:
            return jsonify({"error_message": "Search with no query"}), 400

        resources = list(ResourceManager.search_by_name(query))

        for resource in resources:
            if resource.get("hash"):
                resource["canonical_name"] = resource.get("hash")
            resource["projects"] = []
            for project in Projects.search_resource_in_projects(resource["_id"]):
                resource["projects"].append(project)

        return bson.json_util.dumps(resources)

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Server error :("}), 400
