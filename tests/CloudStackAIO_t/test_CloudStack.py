from CloudStackAIO.CloudStack import CloudStack
from CloudStackAIO.CloudStack import CloudStackClientException

from aiohttp import web
from unittest import TestCase

import asyncio


class TestCloudStack(TestCase):
    event_loop = asyncio.get_event_loop()
    runner = None

    @classmethod
    def setUpClass(cls):
        routes = web.RouteTableDef()

        def async_handler(url_parameters):
            response = {1: web.json_response(dict(query_async_job_result=dict(jobstatus=1, jobresultcode=0,
                                                                              jobresult=dict(text="Hello, world")))),
                        2: web.json_response(dict(query_async_job_result=dict(jobstatus=1, jobresultcode=255,
                                                                              errorcode=255,
                                                                              errortext="Test Failed Return Code!"))),
                        3: web.json_response(dict(query_async_job_result=dict(jobstatus=1, jobresultcode=0,
                                                                              errorcode=254,
                                                                              errortext="Test Failed No Job Result!")))}
            return response[int(url_parameters.get("jobid"))]

        def list_handler(url_parameters):
            response = {1: web.json_response(dict(list_test_response=dict(count=500,
                                                                          response=[dict(test1=1, test2=2), ]))),
                        2: web.json_response(dict(list_test_response=dict(count=400,
                                                                          response=[dict(test3=3, test4=4), ])))
                        }
            return response[int(url_parameters.get('page'))]

        def list_handler_empty_paginated(url_parameters):
            response = {1: web.json_response(dict(list_test_response=dict(count=500,
                                                                          response=[dict(test1=1, test2=2), ]))),
                        2: web.json_response(dict(list_test_response=dict(count=500,
                                                                          response=[dict(test3=3, test4=4), ]))),
                        3: web.json_response(dict(list_test_response=dict())),
                        }
            return response[int(url_parameters.get('page'))]

        @routes.get('/compute')
        async def compute(request):
            response = {'echo': lambda x: web.json_response(dict(echoresponse=dict(x.items()))),
                        'hello': lambda x: web.json_response(dict(helloresponse=dict(text="Hello, world"))),
                        'nojson': lambda x: web.Response(text="This is not a json response!"),
                        'async_ok': lambda x: web.json_response(dict(async_ok_response=dict(jobid=1))),
                        'async_failed_return_code': lambda x: web.json_response(dict(async_ok_response=dict(jobid=2))),
                        'async_missing_results': lambda x: web.json_response(dict(async_ok_response=dict(jobid=3))),
                        'queryAsyncJobResult': async_handler,
                        'list_tests': list_handler,
                        'list_tests_empty_paginated': list_handler_empty_paginated,
                        'list_tests_empty': lambda x: web.json_response(dict(list_test_response=dict()))}
            return response[request.rel_url.query.get('command')](request.rel_url.query)

        app = web.Application()
        app.add_routes(routes)
        cls.runner = web.AppRunner(app)
        cls.event_loop.run_until_complete(cls.start_server())

    @classmethod
    def tearDownClass(cls):
        cls.event_loop.run_until_complete(cls.stop_server())

    @classmethod
    async def start_server(cls):
        await cls.runner.setup()
        site = web.TCPSite(cls.runner, 'localhost', 8080)
        await site.start()

    @classmethod
    async def stop_server(cls):
        await cls.runner.cleanup()

    def setUp(self):
        self.cloud_stack_client = CloudStack(end_point="http://localhost:8080/compute", api_key='Test',
                                             api_secret='Test', event_loop=self.event_loop, async_poll_latency=0)
        self.test_params = {'command': 'echo', 'Test_Image': 'Vm_Image_Centos', 'Test_Disk': '20', 'Test_Memory': '100',
                            'apikey': 'Test', 'response': 'json', 'pagesize': '500', 'page': '1',
                            'signature': 'bw/an0XOIvGmxoGX4qh5GOPj9G8='}

    def test_hello_world_request(self):
        response = asyncio.ensure_future(self.cloud_stack_client.request(command="hello"), loop=self.event_loop)
        self.assertEqual(self.event_loop.run_until_complete(response), {'text': 'Hello, world'})

    def test_url_with_params(self):
        response = asyncio.ensure_future(self.cloud_stack_client.request(**self.test_params),
                                         loop=self.event_loop)
        self.assertEqual(self.event_loop.run_until_complete(response), self.test_params)

    def test_hello_world_getattr(self):
        response = asyncio.ensure_future(self.cloud_stack_client.hello(), loop=self.event_loop)
        self.assertEqual(self.event_loop.run_until_complete(response), {'text': 'Hello, world'})

    def test_url_with_params_getattr(self):
        response = asyncio.ensure_future(self.cloud_stack_client.echo(**self.test_params), loop=self.event_loop)
        self.assertEqual(self.event_loop.run_until_complete(response), self.test_params)

    def test_signature_of_params(self):
        test_signature = self.test_params['signature']

        test_params = self.cloud_stack_client._sign(self.test_params)
        self.assertEqual(test_params['signature'], test_signature)

    def test_no_json_response_getattr(self):
        response = asyncio.ensure_future(self.cloud_stack_client.nojson(), loop=self.event_loop)
        with self.assertRaises(CloudStackClientException) as context:
            self.event_loop.run_until_complete(response)
        self.assertEqual(context.exception.message, "Could not decode content. Server did not return json content!")

    def test_no_json_response(self):
        response = asyncio.ensure_future(self.cloud_stack_client.request(command='nojson'), loop=self.event_loop)
        with self.assertRaises(CloudStackClientException) as context:
            self.event_loop.run_until_complete(response)
        self.assertEqual(context.exception.message, "Could not decode content. Server did not return json content!")

    def test_async_response_okay(self):
        response = asyncio.ensure_future(self.cloud_stack_client.request(command='async_ok'), loop=self.event_loop)
        self.assertEqual(self.event_loop.run_until_complete(response), {'text': 'Hello, world'})

    def test_async_response_okay_getattr(self):
        response = asyncio.ensure_future(self.cloud_stack_client.async_ok(), loop=self.event_loop)
        self.assertEqual(self.event_loop.run_until_complete(response), {'text': 'Hello, world'})

    def test_async_response_failed_return_code(self):
        response = asyncio.ensure_future(self.cloud_stack_client.request(command='async_failed_return_code'),
                                         loop=self.event_loop)
        with self.assertRaises(CloudStackClientException) as context:
            self.event_loop.run_until_complete(response)
        exception = context.exception
        self.assertEqual(exception.message, "Async CloudStack call failed!")
        self.assertEqual(exception.error_code, 255)
        self.assertEqual(exception.error_text, "Test Failed Return Code!")
        self.assertEqual(str(exception), "(message={}, errorcode={}, errortext={})".format(exception.message,
                                                                                           exception.error_code,
                                                                                           exception.error_text))
        self.assertEqual(repr(exception), str(exception))

    def test_async_response_missing_results(self):
        response = asyncio.ensure_future(self.cloud_stack_client.request(command='async_missing_results'),
                                         loop=self.event_loop)
        with self.assertRaises(CloudStackClientException) as context:
            self.event_loop.run_until_complete(response)
        exception = context.exception
        self.assertEqual(exception.message, "Async CloudStack call failed!")
        self.assertEqual(exception.error_code, 254)
        self.assertEqual(exception.error_text, "Test Failed No Job Result!")
        self.assertEqual(str(exception), "(message={}, errorcode={}, errortext={})".format(exception.message,
                                                                                           exception.error_code,
                                                                                           exception.error_text))
        self.assertEqual(repr(exception), str(exception))

    def test_closing_session_with_running_loop(self):
        async def async_sleep():
            await asyncio.ensure_future(self.cloud_stack_client.hello(), loop=self.event_loop)
            del self.cloud_stack_client
            await asyncio.sleep(0.1)
        self.event_loop.run_until_complete(async_sleep())

    def test_paginated_list_api_call(self):
        response = asyncio.ensure_future(self.cloud_stack_client.list_tests())
        self.assertEqual(self.event_loop.run_until_complete(response), {'count': 900,
                                                                        'response': [dict(test1=1, test2=2),
                                                                                     dict(test3=3, test4=4)]})

    def test_empty_list_api_call(self):
        response = asyncio.ensure_future(self.cloud_stack_client.list_tests_empty())
        self.assertEqual(self.event_loop.run_until_complete(response), {})

    def test_empty_paginated_list_api_call(self):
        response = asyncio.ensure_future(self.cloud_stack_client.list_tests_empty_paginated())
        self.assertEqual(self.event_loop.run_until_complete(response), {'count': 1000,
                                                                        'response': [dict(test1=1, test2=2),
                                                                                     dict(test3=3, test4=4)]})
