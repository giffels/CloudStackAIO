from .Utilities import add_signature
from .Utilities import Looper

from functools import partial

import asyncio
import aiohttp


class CloudStack(object):
    def __init__(self, end_point):
        self.end_point = end_point
        self.event_loop = Looper().get_event_loop()
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

    @add_signature('test')
    async def request(self, api, params=None):
        async with self.client_session.get("{}/{}".format(self.end_point, api), params=params) as response:
            return await response.text()
