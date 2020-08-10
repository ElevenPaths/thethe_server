import bson
import time

import server.utils.tokenizer as tokenizer

from server.db import DB
from server.entities.project import Project
from server.utils.password import hash_password, check_password, verify_password


class UsersManager:
    @staticmethod
    def get_users():
        db = DB("users")
        return db.collection.find({}, {"password": False, "project_refs": False})

    @staticmethod
    def create_user(user):
        db = DB("users")
        ts = time.time()

        username = user.get("username")
        password1 = user.get("password1")
        password2 = user.get("password2")
        admin = user.get("admin")
        permissions = user.get("permissions")

        # Fields check
        if not (username and password1 and password2):
            return (False, "Complete required fields please")

        # Username uniqueness
        username_exists = db.collection.find_one({"username": username})
        if username_exists:
            return (False, "This username already exists")

        # Username check
        if len(username) < 4 or len(username) > 64 or not username.isalnum():
            return (False, "Username must be between 4 and 64 alphanumeric characters")

        # Password check
        success, message = check_password(password1, password2)
        if not success:
            return (success, message)

        # Permissions check
        sucess, message = UsersManager.check_permissions(user)
        if not success:
            return (success, message)

        db.collection.insert_one(
            {
                "username": username,
                "password": hash_password(password1),
                "admin": admin,
                "permissions": permissions,
                "created_at": ts,
                "last_edit": ts,
                "disabled": False,
                "disabled_since": None,
            }
        )

        return (success, "User created")

    @staticmethod
    def initial_user_exists():
        db = DB("users")
        count = db.collection.count_documents({})
        print("[initial_user_exists] Checking initial user")

        # There is not an initial user
        if count == 0:
            print("[initial_user_exists] No init user")
            return False

        # Check if at least one user is admin
        result = db.collection.count_documents({"admin": {"$exists": True}})
        if result == 0:
            result = db.collection.find({})

            ts = time.time()
            permissions = {
                "tags": True,
                "projects": True,
                "resources": True,
                "readonly": False,
            }

            for user in result:

                _id = bson.ObjectId(user["_id"])
                db.collection.replace_one(
                    {"_id": bson.ObjectId(_id)},
                    {
                        "_id": _id,
                        "username": user["username"],
                        "password": user["password"],
                        "admin": True,
                        "permissions": permissions,
                        "created_at": ts,
                        "last_edit": ts,
                        "disabled": False,
                        "disabled_since": None,
                    },
                )
        return True

    @staticmethod
    def authenticate(username, password):
        db = DB("users")
        cursor = db.collection.find_one({"username": username})
        if cursor:
            password_hash = cursor["password"]
            is_admin = cursor.get("admin") or False
            permissions = cursor.get("permissions") or {}
            if verify_password(password, password_hash):

                data = {
                    "_id": str(cursor["_id"]),
                    "is_admin": is_admin,
                    "permissions": permissions,
                    "username": username,
                }

                token = tokenizer.generate_auth_token(data)
                return token
        return None

    @staticmethod
    def check_permissions(user):
        admin = user.get("admin")
        readonly, tags, projects, resources = [
            user.get("permissions").get("readonly"),
            user.get("permissions").get("tags"),
            user.get("permissions").get("projects"),
            user.get("permissions").get("resources"),
        ]

        message = "Successfuly created new user"

        # Admin should have all permissions enabled and not readonly
        if admin:
            valid = not readonly and (tags, projects, resources)
            if not valid:
                message = "Admin should have all permissions enabled"
        # Readonly account should have no permissions but readonly
        elif readonly:
            valid = not (any([tags, projects, resources]))
            if not valid:
                message = "Readonly users must have no write permissions"
        # Not admin and not readonly account should have at least 1 permission
        elif not admin and not readonly:
            valid = any([tags, projects, resources])
            if not valid:
                message = "User must have enabled one permission at least"
        # Default is not valid
        else:
            valid = False
            message = "Permission configuration not valid"

        if valid:
            return (True, message)
        else:
            return (False, message)


class User:
    def __init__(self, user_id):
        self.user_id = bson.ObjectId(user_id)
        self.db = DB("users")

    def delete(self):
        result = self.db.collection.delete_one({"_id": self.user_id})
        if result:
            return (True, "User deleted")
        else:
            return (False, "Unable to delete user")

    def toggle_disable(self):
        user = self.db.collection.find_one({"_id": self.user_id})
        if user:
            if user.get("disabled"):
                self.db.collection.update(
                    {"_id": self.user_id},
                    {"$set": {"disabled": False, "disabled_since": None}},
                )
                return (True, "User enabled")
            else:
                self.db.collection.update(
                    {"_id": self.user_id},
                    {"$set": {"disabled": True, "disabled_since": time.time()}},
                )
            return (True, "User disabled")
        else:
            return (False, "Uknown user id")

    def change_perm(self, proto_user):
        user = self.db.collection.find_one({"_id": self.user_id})
        if user:
            if user.get("disabled"):
                return (False, "User is disabled")

            valid, message = UsersManager.check_permissions(proto_user)
            if not valid:
                return (valid, message)
            else:
                self.db.collection.update_one(
                    {"_id": self.user_id},
                    {
                        "$set": {
                            "permissions": proto_user.get("permissions"),
                            "admin": proto_user.get("admin"),
                        }
                    },
                )
            return (True, "Permission changed")
        else:
            return (False, "Error changing permissions")

    def change_password(self, old_password, password1, password2):
        user = self.db.collection.find_one({"_id": self.user_id})
        if user:
            password_hash = user["password"]
            if not verify_password(old_password, password_hash):
                return (False, "Old password failed")

            self.db.collection.update(
                {"_id": self.user_id}, {"$set": {"password": hash_password(password1)}},
            )
            return (True, "Successfully changed password")

        return (False, "Unknown user")

    def get_active_project(self):
        result = self.db.collection.find_one(
            {"_id": self.user_id}, {"active_project": 1}
        )

        if not result or not "active_project" in result:
            return None

        return Project(result["active_project"])

    def set_active_project(self, project_id):
        project_id = bson.ObjectId(project_id)
        active_project = self.db.collection.find_one_and_update(
            {"_id": self.user_id}, {"$set": {"active_project": project_id}}
        )
        Project(project_id).set_open_timestamp()
        return active_project

    # TODO: Make a route when user is switching back to project selection or logout
    def reset_active_project(self):
        project_id = bson.ObjectId(project_id)
        return self.db.collection.find_one_and_update(
            {"_id": self.user_id}, {"$set": {"active_project": None}}
        )

    def add_project(self, project_id):
        self.__project_refs(project_id, "$addToSet")

    def remove_project(self, project_id):
        self.__project_refs(project_id, "$pull")

    def __project_refs(self, project_id, operation):
        project_id = bson.ObjectId(project_id)
        return self.db.collection.find_one_and_update(
            {"_id": self.user_id}, {operation: {"project_refs": project_id}}
        )

    def get_projects(self):
        projects = self.db.collection.find_one(
            {"_id": self.user_id}, {"project_refs": 1}
        )
        if not projects:
            return None
        else:
            return projects.get("project_refs")
