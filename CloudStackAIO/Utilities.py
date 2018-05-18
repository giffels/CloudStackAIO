from urllib.parse import quote
from urllib.parse import urlencode

import hashlib
import hmac
import base64


def add_signature(secret_key):
    def signature_decorator(f):
        def wrapper(*args, **kwargs):
            try:
                url_params = kwargs['params']
            except KeyError:
                pass
            else:
                request_string = urlencode(url_params, safe='*', quote_via=quote).lower()
                digest = hmac.new(secret_key.encode('utf-8'), request_string.encode('utf-8'), hashlib.sha1).digest()
                url_params['signature'] = quote(base64.b64encode(digest).decode('utf-8').strip())
            finally:
                return f(*args, **kwargs)
        return wrapper
    return signature_decorator
