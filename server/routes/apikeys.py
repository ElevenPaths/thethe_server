import time
import bson
import json
import traceback

from bson.json_util import dumps
from flask import Blueprint, request, abort, jsonify

from server.db import DB
from server.utils.tokenizer import token_required
from server.entities.plugin_manager import PluginManager

apikeys_api = Blueprint("apikeys", __name__)


@apikeys_api.route("/api/get_apikeys", methods=["POST"])
@token_required
def get_apikeys(user):
    try:
        if not user.get("is_admin"):
            return jsonify({"error_message": "User is not admin"}), 400

        results = DB("apikeys").collection.find({}, {"_id": False})
        plugins = PluginManager.get_all()
        plugins = [plugin for plugin in list(plugins) if plugin.get("needs_apikey")]

        list_results = list(results)

        for plugin in plugins:
            apikey_names = plugin.get("apikey_names")
            apikeys = []
            for apikey_name in apikey_names:
                apikey = {}
                apikey_value = [
                    value["apikey"]
                    for value in list_results
                    if value["name"] == apikey_name
                ]
                apikey["name"] = apikey_name
                apikey["value"] = apikey_value[0] if len(apikey_value) > 0 else None
                apikeys.append(apikey)

            plugin["apikeys"] = apikeys

        return dumps(plugins)

    except Exception as e:
        print(e)
        return jsonify({"error_message": "Error getting API keys"}), 400


@apikeys_api.route("/api/upload_apikeys", methods=["POST"])
@token_required
def upload_apikeys(user):
    try:
        apikeys = request.json["entries"]
        for apikey in apikeys:
            result = DB("apikeys").collection.update_one(
                {"name": apikey["name"]},
                {"$set": {"apikey": apikey["value"].strip()}},
                upsert=True,
            )

            # Also updating "plugins" metadata
            plugins = DB("plugins")
            plugin = plugins.collection.update_one(
                {"apikey_names": apikey["name"]}, {"$set": {"apikey_in_ddbb": True}}
            )

        return json.dumps({"success_message": "Apikeys saved"}, default=str)

    except Exception as e:
        print(f"[routes/apikeys.upload_apikeys]: {e}")
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Error uploading API keys"}), 400
