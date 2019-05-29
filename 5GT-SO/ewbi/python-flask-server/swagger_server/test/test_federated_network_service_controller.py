# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.federated_info import FederatedInfo  # noqa: E501
from swagger_server.models.inline_response2001 import InlineResponse2001  # noqa: E501
from swagger_server.models.inline_response2002 import InlineResponse2002  # noqa: E501
from swagger_server.models.interconnection_paths import InterconnectionPaths  # noqa: E501
from swagger_server.test import BaseTestCase


class TestFederatedNetworkServiceController(BaseTestCase):
    """FederatedNetworkServiceController integration test stubs"""

    def test_federated_connection_paths(self):
        """Test case for federated_connection_paths

        Query towards the federated/provider domain to perform connections towards the local and other federate domains
        """
        body = InterconnectionPaths()
        response = self.client.open(
            '/5gt/so-ewbi/v1/ns/{nsId}/federated-internested-connections'.format(nsId='nsId_example'),
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_federated_instance_info(self):
        """Test case for federated_instance_info

        Query towards the federated/provider domain to know info about: CIDR/pools that have to be used/not used in the federated domain
        """
        body = FederatedInfo()
        response = self.client.open(
            '/5gt/so-ewbi/v1/ns/{nsId}/federated-instance-info'.format(nsId='nsId_example'),
            method='PUT',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_federated_network_info(self):
        """Test case for federated_network_info

        Query towards the consumer/local domain about the information: CIDR/pools that have to be used/not used in the federated domain
        """
        body = FederatedInfo()
        response = self.client.open(
            '/5gt/so-ewbi/v1/ns/{nsId}/federated-network-info'.format(nsId='nsId_example'),
            method='PUT',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
