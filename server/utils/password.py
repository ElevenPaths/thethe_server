import traceback

from zxcvbn import zxcvbn
from passlib.apps import custom_app_context as pwd_context

MIN_PASSWORD_LENGHT = 8


def check_password(password1, password2=None):
    if password2:
        if not password1 == password2:
            return (False, "New password does not match")

    if len(password1) < MIN_PASSWORD_LENGHT:
        return (False, f"New password must be {MIN_PASSWORD_LENGHT} at least")

    if not check_pass_strengh(password1):
        return (
            False,
            f"Password is not strong enough. Min {MIN_PASSWORD_LENGHT} chars length. Mix alphanums and symbols",
        )

    return (True, "Password is valid")


def check_pass_strengh(candidate_pass):
    try:
        if not candidate_pass:
            return False
        result = zxcvbn(candidate_pass)
        if result.get("score") >= 2:
            return True
        return False

    except Exception as e:
        tb1 = traceback.TracebackException.from_exception(e)
        print("[_check_pass_strengh]")
        print("".join(tb1.format()))


def hash_password(password):
    password_hash = pwd_context.hash(password)
    return password_hash


def verify_password(password, password_hash):
    return pwd_context.verify(password, password_hash)
