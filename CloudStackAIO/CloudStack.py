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
    """
    CloudStackClientException used to propagate errors occurred during the processing of CloudStack API calls.
    """
    def __init__(self, message: str, error_code: str=None, error_text: str=None, response: dict=None):
        self.message = message
        self.error_code = error_code
        self.error_text = error_text
        self.response = response

    def __str__(self) -> str:
        """
        Define string representation of the CloudStackClientException
        :return: String containing a message, the error code as well as the error text
        :rtype: str
        """
        return "(message={}, errorcode={}, errortext={})".format(self.message, self.error_code, self.error_text)

    def __repr__(self) -> str:
        """
        Define representation of the CloudStackClientException
        :return: String containing a message, the error code as well as the error text
        :rtype: str
        """
        return str(self)


class CloudStack(object):
    def __init__(self, end_point: str, api_key: str, api_secret: str, event_loop: asyncio.AbstractEventLoop,
                 async_poll_latency: int=2, max_page_size: int=500) -> None:
        """
        Client object to access a CloudStack API

        :param end_point: URL to reach the CloudStack API
        :type end_point: str
        :param api_key: APIKey to access the CloudStack API (usually available from your cloud provider)
        :type api_key: str
        :param api_secret: Secret to access the CloudStack API (usually available from your cloud provider)
        :param event_loop: asyncio event loop to utilize
        :type event_loop: asyncio.AbstractEventLoop
        :param async_poll_latency: Time in seconds to wait before polling CloudStack API to fetch results of
                                   asynchronous API calls
        :type async_poll_latency: int
        :param max_page_size: Some API calls are paginated like listVirtualMachines, this number specifies the maximum
                              number of item returned in one API call. The client automatically takes care of the
                              pagination by splitting it into separate API calls and returns the entire list
        :type max_page_size: int

        :Example:

        .. code-block:: python

           event_loop = asyncio.get_event_loop()
           cloud_stack_client = CloudStack(end_point='https://api.exoscale.ch/compute',
                                           api_key='<Your API key>',
                                           api_secret='Your API secret',
                                           event_loop=event_loop)
        """
        self.end_point = end_point
        self.api_key = api_key
        self.api_secret = api_secret
        self.event_loop = event_loop
        self.async_poll_latency = async_poll_latency
        self.max_page_size = max_page_size
        self.client_session = aiohttp.ClientSession(loop=self.event_loop)

    def __del__(self) -> None:
        """
        Deletion function taking care that the used sessions is closed before the deleting the object. This is
        mandatory according to the aiohttp documentation. The deletion function is thus scheduling a task that takes
        care of closing the session. Depending wether an event loop is already running, the task is either scheduled or
        a new event loop is started.
        """
        try:
            self.event_loop.run_until_complete(self._close_session())
        except RuntimeError:
            self.event_loop.create_task(self._close_session())

    async def _close_session(self) -> None:
        """
        According to the aiohttp documentation all opened sessions need to be closed, before leaving the program. This
        function takes care that the client session is closed. This async co-routine is automatically scheduled, when
        the client object is destroyed.
        """
        await self.client_session.close()
        await asyncio.sleep(0.25)  # http://aiohttp.readthedocs.io/en/stable/client_advanced.html#graceful-shutdown

    def __getattr__(self, command: str) -> Callable:
        """
        This allows to support any available and future CloudStack API in this client. The returned partial function can
        directly be used to call the corresponding CloudStack API including all supported parameters.

        :param command: Command string indicating the CloudStack API to be called.
        :type command: str
        :return: Partial function that can be used the call the CloudStack API specified in the command string.
        """
        return partial(self.request, command=command)

    async def request(self, command: str, **kwargs) -> dict:
        """
        Async co-routine to perform requests to a CloudStackAPI. The parameters needs to include the command string,
        which refers to the API to be called. In principle any available and future CloudStack API can be called. The
        `**kwargs` magic allows us to all add supported parameters to the given API call. A list of all available APIs
        can found at https://cloudstack.apache.org/api/apidocs-4.8/TOC_User.html

        :param command: Command string indicating the CloudStack API to be called.
        :type command: str
        :param kwargs: Parameters to be passed to the CloudStack API
        :return: Dictionary containing the decoded json reply of the CloudStack API
        :rtype: dict
        """
        kwargs.update(dict(apikey=self.api_key, command=command, response='json'))

        if 'list' in command.lower():  # list APIs can be paginated, therefore include max_page_size and page parameter
            kwargs.update(dict(pagesize=self.max_page_size, page=1))

        final_data = dict()
        while True:
            async with self.client_session.get(self.end_point, params=self._sign(kwargs)) as response:
                data = await self._handle_response(response=response,
                                                   await_final_result='queryasyncjobresult' not in command.lower())
                try:
                    count = data.pop('count')
                except KeyError:
                    if not data:
                        # Empty dictionary is returned in case a query does not contain any results.
                        # Can happen also if a listAPI is called with a page that does not exits. Therefore, final_data
                        # has to be returned in order to return all results from preceding pages.
                        return final_data
                    else:
                        # Only list API calls have a 'count' key inside the response,
                        # return data as it is in other cases!
                        return data
                else:
                    # update final_data using paginated results, dictionaries of the response contain the count key
                    # and one key pointing to the actual data values
                    for key, value in data.items():
                        final_data.setdefault(key, []).extend(value)
                    final_data['count'] = final_data.setdefault('count', 0) + count
                    kwargs['page'] += 1
                    if count < self.max_page_size:  # no more pages exists
                        return final_data

    async def _handle_response(self, response: aiohttp.client_reqrep.ClientResponse, await_final_result: bool) -> dict:
        """
        Handles the response returned from the CloudStack API. Some CloudStack API are implemented asynchronous, which
        means that the API call returns just a job id. The actually expected API response is postponed and a specific
        asyncJobResults API has to be polled using the job id to get the final result once the API call has been
        processed.

        :param response: The response returned by the aiohttp call.
        :type response: aiohttp.client_reqrep.ClientResponse
        :param await_final_result: Specifier that indicates whether the function should poll the asyncJobResult API
                                   until the asynchronous API call has been processed
        :type await_final_result: bool
        :return: Dictionary containing the JSON response of the API call
        :rtype: dict
        """
        try:
            data = await response.json()
        except aiohttp.client_exceptions.ContentTypeError:
            text = await response.text()
            logging.debug('Content returned by server not of type "application/json"\n Content: {}'.format(text))
            raise CloudStackClientException(message="Could not decode content. Server did not return json content!")
        else:
            data = self._transform_data(data)

        while await_final_result and ('jobid' in data):
            await asyncio.sleep(self.async_poll_latency)
            data = await self.queryAsyncJobResult(jobid=data['jobid'])
            if data['jobstatus']:  # jobstatus is 0 for pending async CloudStack calls
                if not data['jobresultcode']:  # exit code is zero
                    try:
                        return data['jobresult']
                    except KeyError:
                        pass
                logging.debug("Async CloudStack call returned {}".format(str(data)))
                raise CloudStackClientException(message="Async CloudStack call failed!",
                                                error_code=data.get("errorcode"),
                                                error_text=data.get("errortext"),
                                                response=data)

        return data

    def _sign(self, url_parameters: dict) -> dict:
        """
        According to the CloudStack documentation, each request needs to be signed in order to authenticate the user
        account executing the API command. The signature is generated using a combination of the api secret and a SHA-1
        hash of the url parameters including the command string. In order to generate a unique identifier, the url
        parameters have to be transformed to lower case and ordered alphabetically.

        :param url_parameters: The url parameters of the API call including the command string
        :type url_parameters: dict
        :return: The url parameters including a new key, which contains the signature
        :rtype: dict
        """
        if url_parameters:
            url_parameters.pop('signature', None)  # remove potential existing signature from url parameters
            request_string = urlencode(sorted(url_parameters.items()), safe='.-*_', quote_via=quote).lower()
            digest = hmac.new(self.api_secret.encode('utf-8'), request_string.encode('utf-8'), hashlib.sha1).digest()
            url_parameters['signature'] = base64.b64encode(digest).decode('utf-8').strip()
        return url_parameters

    @staticmethod
    def _transform_data(data: dict) -> dict:
        """
        Each CloudStack API call returns a nested dictionary structure. The first level contains only one key indicating
        the API that originated the response. This function removes that first level from the data returned to the
        caller.

        :param data: Response of the API call
        :type data: dict
        :return: Simplified response without the information about the API that originated the response.
        :rtype: dict
        """
        for key in data.keys():
            return data[key]
