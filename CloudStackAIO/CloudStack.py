from functools import partial
from urllib.parse import quote
from urllib.parse import urlencode

import asyncio
import aiohttp
import hashlib
import hmac
import base64


class CloudStack(object):
    def __init__(self, end_point, api_key, secret, event_loop):
        self.end_point = end_point
        self.api_key = api_key
        self.secret = secret
        self.event_loop = event_loop
        self.client_session = aiohttp.ClientSession(loop=self.event_loop)

    def __del__(self):
        try:
            self.event_loop.run_until_complete(self.close_session())
        except RuntimeError:
            self.event_loop.create_task(self.close_session())

    async def close_session(self):
        await self.client_session.close()
        await asyncio.sleep(0.25)  # http://aiohttp.readthedocs.io/en/stable/client_advanced.html#graceful-shutdown

    def __getattr__(self, api):
        return partial(self.request, api=api)

    async def request(self, api, **kwargs):
        async with self.client_session.get("{}/{}".format(self.end_point, api), params=self.sign(kwargs)) as response:
            return await response.text()

    def sign(self, url_parameters):
        if url_parameters:
            try:
                del url_parameters['signature']  # remove possible existing signature from url parameters
            except KeyError:
                pass
            finally:
                request_string = urlencode(url_parameters, safe='*', quote_via=quote).lower()
                digest = hmac.new(self.secret.encode('utf-8'), request_string.encode('utf-8'), hashlib.sha1).digest()
                url_parameters['signature'] = base64.b64encode(digest).decode('utf-8').strip()
        return url_parameters
