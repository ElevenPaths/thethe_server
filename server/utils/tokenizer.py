import os
import sys

_SECRET_KEY = os.environ["THETHE_SECRET"]

from itsdangerous import (
    TimedJSONWebSignatureSerializer as Serializer,
    BadSignature,
    SignatureExpired,
)


# TODO: Change expiration time when in production
def generate_auth_token(user_id, expiration=600000):
    s = Serializer(_SECRET_KEY, expires_in=expiration)
    return s.dumps({"id": user_id})


def verify_auth_token(token):
    s = Serializer(_SECRET_KEY)
    try:
        user = None
        user = s.loads(token)
        return user
    except SignatureExpired:
        print("[!] Invalid token: SignatureExpired")
    except BadSignature:
        print("[!] Invalid token: BadSignature")
    finally:
        return user
