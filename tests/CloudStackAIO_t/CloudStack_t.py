from CloudStackAIO.CloudStack import CloudStack

from aiohttp import web
from unittest import TestCase

import asyncio


class CloudStack_t(TestCase):
    event_loop = asyncio.get_event_loop()
    runner = None

    @classmethod
    def setUpClass(cls):
        routes = web.RouteTableDef()

        @routes.get('/compute')
        async def compute(request):
            response = {'echo': web.json_response(dict(echoresponse=dict(request.rel_url.query.items()))),
                        'hello': web.json_response(dict(helloresponse=dict(text="Hello, world"))),
                        'nojson': web.Response(text="This is not a json response!")}
            return response[request.rel_url.query.get('command')]

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
                                             api_secret='Test', event_loop=self.event_loop)
        self.test_params = {'command': 'echo', 'Test_Image': 'Vm_Image_Centos', 'Test_Disk': '20', 'Test_Memory': '100',
                            'apikey': 'Test', 'signature': 'RXhS9/EhfioAVwNNtkzVS5wojm0='}

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
        test_signature = 'RXhS9/EhfioAVwNNtkzVS5wojm0='

        test_params = self.cloud_stack_client.sign(self.test_params)
        self.assertEqual(test_params['signature'], test_signature)

    def test_no_json_response_getattr(self):
        response = asyncio.ensure_future(self.cloud_stack_client.nojson(), loop=self.event_loop)
        self.assertEqual(self.event_loop.run_until_complete(response), {'server_msg': 'This is not a json response!'})

    def test_no_json_response(self):
        response = asyncio.ensure_future(self.cloud_stack_client.request(command='nojson'), loop=self.event_loop)
        self.assertEqual(self.event_loop.run_until_complete(response), {'server_msg': 'This is not a json response!'})
