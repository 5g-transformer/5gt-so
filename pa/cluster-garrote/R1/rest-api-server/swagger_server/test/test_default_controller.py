# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.pa_request import PARequest  # noqa: E501
from swagger_server.models.pa_response import PAResponse  # noqa: E501
from swagger_server.test import BaseTestCase


class TestDefaultController(BaseTestCase):
    """DefaultController integration test stubs"""

    def test_p_a_comp_get(self):
        """Test case for p_a_comp_get

        Retrieve a list of PA execution requests
        """
        response = self.client.open(
            '/5gt/so/v1/PAComp',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_p_a_comp_post(self):
        """Test case for p_a_comp_post

        Request the execution of a placement algorithm.
        """
        PARequest = PARequest()
        response = self.client.open(
            '/5gt/so/v1/PAComp',
            method='POST',
            data=json.dumps(PARequest),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_p_a_comp_req_id_get(self):
        """Test case for p_a_comp_req_id_get

        Retrieve a specific PA request
        """
        response = self.client.open(
            '/5gt/so/v1/PAComp/{ReqId}'.format(ReqId='ReqId_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
