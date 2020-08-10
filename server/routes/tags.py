import time
import bson
import json
import traceback
import urllib.parse


from flask import Blueprint, request, abort, jsonify

from server.utils.tokenizer import token_required

from server.entities.resource_manager import ResourceManager
from server.entities.user import User
from server.entities.tags import TagManager

tags_api = Blueprint("tags", __name__)


@tags_api.route("/api/get_tags", methods=["POST"])
@token_required
def get_tags(user):
    try:
        tags = TagManager.get_tags()
        return bson.json_util.dumps(tags)

    except Exception as e:
        print(e)
        return jsonify({"error_message": "Error getting global tags"}), 400


@tags_api.route("/api/create_tag", methods=["POST"])
@token_required
def create_tag(user):
    try:
        can_manage_tags = user.get("permissions").get("tags")
        if not can_manage_tags:
            return (
                jsonify({"error_message": "You don't have permissions to manage tags"}),
                400,
            )

        tag = request.json.get("tag")

        valid, message = TagManager.create(tag)

        if valid:
            return jsonify({"success_message": message})

        return jsonify({"error_message": message}), 400

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Error creating tag"}), 400


@tags_api.route("/api/delete_tag", methods=["POST"])
@token_required
def delete_tag(user):
    try:
        can_manage_tags = user.get("permissions").get("tags")
        if not can_manage_tags:
            return (
                jsonify({"error_message": "You don't have permissions to manage tags"}),
                400,
            )

        tag_id = request.json.get("tag_id")

        success, message = TagManager.delete(bson.ObjectId(tag_id))
        if success:
            return jsonify({"success_message": message})
        else:
            return jsonify({"error_message": message}), 400

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Error deleting tag"}), 400


@tags_api.route("/api/add_tag", methods=["POST"])
@token_required
def add_tag(user):
    try:
        resource_id = request.json["resource_id"]
        tag_id = request.json["tag_id"]

        resource = ResourceManager.get(resource_id)

        resource.add_tag(tag_id)

        return jsonify({"success_message": "Tag added to resource"})

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Error adding tag"}), 400


@tags_api.route("/api/remove_tag", methods=["POST"])
@token_required
def remove_tag(user):
    try:
        resource_id = request.json["resource_id"]
        tag_id = request.json["tag_id"]

        resource = ResourceManager.get(resource_id)

        if resource.remove_tag(tag_id):
            return jsonify({"success_message": "Tag removed to resource"})

        else:
            return (
                jsonify({"error_message": "There was a problem removing a tag",}),
                400,
            )

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Error removing tag"}), 400
