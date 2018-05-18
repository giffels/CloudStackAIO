from urllib.parse import quote_plus

import asyncio
import hashlib
import hmac
import base64


def add_signature(secret_key):
    def signature_decorator(f):
        def wrapper(self, *args, **kwargs):
            try:
                url_params = kwargs['params']
            except KeyError:
                pass
            else:
                request_string = '&'.join(['='.join([k.lower(), quote_plus(url_params[k].lower().replace('+','%20'),  safe='*')]) for k in sorted(url_params.iterkeys())])
                url_params['signature'] = quote_plus(base64.encodebytes(hmac.new(secret_key, request_string, hashlib.sha1).digest()).strip())
            finally:
                return f(self, *args, **kwargs)
        return wrapper
    return signature_decorator


class Looper(object):
    _shared_state = {}

    def __init__(self):
        if not self._shared_state:
            self._shared_state = self.__dict__
            self.event_loop = asyncio.get_event_loop()

    def get_event_loop(self):
        return self.event_loop
