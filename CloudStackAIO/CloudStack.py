from functools import partial
from urllib.parse import quote
from urllib.parse import urlencode

import asyncio
import aiohttp
import hashlib
import hmac
import base64


class CloudStack(object):
    def __init__(self, end_point, api_key, api_secret, event_loop):
        self.end_point = end_point
        self.api_key = api_key
        self.api_secret = api_secret
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

    def __getattr__(self, command):
        return partial(self.request, command=command)

    async def request(self, command, **kwargs):
        kwargs.update(dict(apikey=self.api_key, command=command))
        async with self.client_session.get(self.end_point, params=self.sign(kwargs)) as response:
            try:
                data = await response.json()
            except aiohttp.client_exceptions.ContentTypeError:
                text = await response.text()
                data = dict(server_response=dict(server_msg=text))
            finally:
                for key in data.keys():
                    return data[key]

    def sign(self, url_parameters):
        if url_parameters:
            url_parameters.pop('signature', None)  # remove potential existing signature from url parameters
            request_string = urlencode(sorted(url_parameters.items()), safe='.-*_', quote_via=quote).lower()
            digest = hmac.new(self.api_secret.encode('utf-8'), request_string.encode('utf-8'), hashlib.sha1).digest()
            url_parameters['signature'] = base64.b64encode(digest).decode('utf-8').strip()
        return url_parameters
