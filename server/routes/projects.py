import bson
import time
import traceback

from flask import Blueprint, request, abort, jsonify, Response

from server.db import DB
from server.utils.tokenizer import token_required

from server.entities.user import User
from server.entities.project import (
    Project,
    Projects,
    ProjectExistException,
    ProjectNameException,
    ProjectNotExistsException,
)

PROJECT_NAME_LIMIT = 64

projects_api = Blueprint("projects", __name__)

@projects_api.route("/api/ping", methods=["POST"])
@token_required
def ping(user):
    try:
        timestamp = time.time()
        active_project = User(user.get("_id")).get_active_project()
        if active_project:
            updates = active_project.get_updates(timestamp)
            return jsonify(updates)
        else:
            return jsonify([])

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Server error :("}), 400

@projects_api.route("/api/get_projects", methods=["POST"])
@token_required
def get_projects(user):
    try:
        projects = Projects.get_project_docs()
        return bson.json_util.dumps(projects)

    except Exception as e:
        print(f"Error when retrieving projects")
        tb1 = traceback.TracebackException.from_exception(e)
        print("".join(tb1.format()))
        return jsonify({"error_message": "Error when retrieving projects"}), 400


@projects_api.route("/api/new_project", methods=["POST"])
@token_required
def new_project(user):
    try:
        name = request.json["name"]
        project_id = Projects.create(name, user.get("_id"))
        User(user.get("_id")).add_project(project_id)

        return jsonify({"success_message": f"New project {name} created"})

    except ProjectNameException:
        print(f"Project name error")
        return (jsonify({"error_message": "Project name error"}), 400)

    except ProjectExistException:
        print(f"Project already exists in database")
        return (
            jsonify({"error_message": "A project with that name already exists"}),
            400,
        )

    except Exception as e:
        print(f"Error when creating new project {e}")
        return jsonify({"error_message": "Error when creating a new project"}), 400


@projects_api.route("/api/rename_project", methods=["POST"])
@token_required
def rename_project(user):
    try:
        project_id = bson.ObjectId(request.json["id"])
        new_name = request.json["new_name"]

        if not new_name.isalnum() or len(new_name) > PROJECT_NAME_LIMIT:
            raise ProjectNameException

        if project_id in User(user.get("_id")).get_projects():
            project = Project(project_id)
            if project.rename(new_name):
                return jsonify({"success_message": f"Successful renaming"})

        return jsonify({"error_message": "The name is not valid"}), 400

    except ProjectNameException as e:
        print(f"Project name error")
        return jsonify({"error_message": "The name is not valid"}), 400

    except Exception as e:
        print(f"Error when renaming project {e}")
        return jsonify({"error_message": "Error when renaming project"}), 400


@projects_api.route("/api/delete_project", methods=["POST"])
@token_required
def delete_project(user):
    try:
        project_id = request.json["project_id"]
        Projects.delete(project_id)
        User(user.get("_id")).remove_project(project_id)

        return jsonify({"success_message": f"Selected project deleted"})

    except ProjectNotExistsException as e:
        print(f"Selected project for deletion does not exists {e}")
        return (
            jsonify(
                {
                    "error_message": "Deletion error: Could not find any project with that ID"
                }
            ),
            400,
        )

    except Exception as e:
        print(f"Error when deleting a project {e}")
        return jsonify({"error_message": "Error during deletion"}), 400


@projects_api.route("/api/set_active_project", methods=["POST"])
@token_required
def set_active_project(user):
    try:
        project_id = request.json["project_id"]
        User(user.get("_id")).set_active_project(project_id)
        return jsonify({})

    except Exception as e:
        print(f"Error when setting an active project {e}")
        return jsonify({"error_message": "Error during active project setting"}), 400


@projects_api.route("/api/get_active_project", methods=["POST"])
@token_required
def get_active_project(user):
    try:
        active_project = User(user.get("_id")).get_active_project()
        if not active_project:
            return jsonify({})
        else:
            return jsonify({"project_id": active_project.get_id()})

    except Exception as e:
        print(f"Error when getting active project {e}")
        return jsonify({"error_message": "Error getting active project"}), 400
