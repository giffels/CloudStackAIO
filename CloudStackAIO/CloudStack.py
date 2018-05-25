from functools import partial
from urllib.parse import quote
from urllib.parse import urlencode
from typing import Callable

import asyncio
import aiohttp
import hashlib
import hmac
import base64
import logging


class CloudStackClientException(Exception):
    pass


class CloudStack(object):
    def __init__(self, end_point: str, api_key: str, api_secret: str,
                 event_loop: asyncio.AbstractEventLoop, async_poll_latency: int=2) -> None:
        self.end_point = end_point
        self.api_key = api_key
        self.api_secret = api_secret
        self.event_loop = event_loop
        self.async_poll_latency = async_poll_latency
        self.client_session = aiohttp.ClientSession(loop=self.event_loop)

    def __del__(self) -> None:
        try:
            self.event_loop.run_until_complete(self.close_session())
        except RuntimeError:
            self.event_loop.create_task(self.close_session())

    async def close_session(self) -> None:
        await self.client_session.close()
        await asyncio.sleep(0.25)  # http://aiohttp.readthedocs.io/en/stable/client_advanced.html#graceful-shutdown

    def __getattr__(self, command: str) -> Callable:
        return partial(self.request, command=command)

    async def request(self, command: str, **kwargs) -> dict:
        kwargs.update(dict(apikey=self.api_key, command=command))
        async with self.client_session.get(self.end_point, params=self.sign(kwargs)) as response:
            return await self.handle_response(response=response,
                                              await_final_result='queryasyncjobresult' not in command.lower())

    async def handle_response(self, response: aiohttp.client_reqrep.ClientResponse, await_final_result: bool) -> dict:
        try:
            data = await response.json()
        except aiohttp.client_exceptions.ContentTypeError:
            text = await response.text()
            logging.debug('Content returned by server not of type "application/json"\n Content: {}'.format(text))
            raise CloudStackClientException("Could not decode content. Server did not return proper json content!")
        else:
            data = self.transform_data(data)

        while await_final_result and ('jobid' in data):
            await asyncio.sleep(self.async_poll_latency)
            data = await self.queryAsyncJobResult(jobid=data['jobid'])
            if data['jobstatus']:  # jobstatus is 0 for pending async CloudStack calls
                if not data['jobresultcode']:  # exit code is zero
                    try:
                        return data['jobresults']
                    except KeyError:
                        pass
                logging.debug("Async CloudStack call returned {}".format(str(data)))
                raise CloudStackClientException("Async CloudStack call failed!")

        return data

    def sign(self, url_parameters: dict) -> dict:
        if url_parameters:
            url_parameters.pop('signature', None)  # remove potential existing signature from url parameters
            request_string = urlencode(sorted(url_parameters.items()), safe='.-*_', quote_via=quote).lower()
            digest = hmac.new(self.api_secret.encode('utf-8'), request_string.encode('utf-8'), hashlib.sha1).digest()
            url_parameters['signature'] = base64.b64encode(digest).decode('utf-8').strip()
        return url_parameters

    @staticmethod
    def transform_data(data: dict) -> dict:
        for key in data.keys():
            return data[key]
