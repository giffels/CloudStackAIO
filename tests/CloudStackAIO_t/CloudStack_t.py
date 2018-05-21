from CloudStackAIO.CloudStack import CloudStack

from aiohttp import web
from unittest import TestCase

import asyncio
import json


class CloudStack_t(TestCase):
    event_loop = asyncio.get_event_loop()
    runner = None

    @classmethod
    def setUpClass(cls):
        routes = web.RouteTableDef()

        @routes.get('/hello')
        async def hello(request):
            return web.Response(text="Hello, world")

        @routes.get('/echo')
        async def echo(request):
            return web.Response(text=json.dumps(dict(request.rel_url.query.items())))

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
        self.cloud_stack_client = CloudStack(end_point="http://localhost:8080", api_key='Test',
                                             secret='Test', event_loop=self.event_loop)
        self.test_params = {'Test_Image': 'vm_image_centos', 'Test_Disk': '20',
                            'Test_Memory': '100', 'signature': 't3Rizjq3rIj+4XBrqY6JReyIxVY='}

    def test_hello_world_request(self):
        response = asyncio.ensure_future(self.cloud_stack_client.request(api="hello"), loop=self.event_loop)
        self.assertEqual(self.event_loop.run_until_complete(response), "Hello, world")

    def test_url_with_params(self):
        response = asyncio.ensure_future(self.cloud_stack_client.request(api="echo", **self.test_params),
                                         loop=self.event_loop)
        self.assertEqual(self.event_loop.run_until_complete(response), json.dumps(self.test_params))

    def test_hello_world_getattr(self):
        response = asyncio.ensure_future(self.cloud_stack_client.hello(), loop=self.event_loop)
        self.assertEqual(self.event_loop.run_until_complete(response), "Hello, world")

    def test_url_with_params_getattr(self):
        response = asyncio.ensure_future(self.cloud_stack_client.echo(**self.test_params), loop=self.event_loop)
        self.assertEqual(self.event_loop.run_until_complete(response), json.dumps(self.test_params))

    def test_signature_of_params(self):
        test_signature = 't3Rizjq3rIj+4XBrqY6JReyIxVY='

        test_params = self.cloud_stack_client.sign(self.test_params)
        self.assertEqual(test_params['signature'], test_signature)
