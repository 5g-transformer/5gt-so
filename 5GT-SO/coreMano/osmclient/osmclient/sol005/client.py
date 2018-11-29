# Copyright 2018 Telefonica
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
OSM SOL005 client API
"""

#from osmclient.v1 import vca
from osmclient.sol005 import vnfd
from osmclient.sol005 import nsd
from osmclient.sol005 import ns
from osmclient.sol005 import vnf
from osmclient.sol005 import vim
from osmclient.sol005 import package
from osmclient.sol005 import http
from osmclient.sol005 import sdncontroller
from osmclient.common.exceptions import ClientException
import json

class Client(object):

    def __init__(
        self,
        host=None,
        so_port=9999,
        so_project='admin',
        ro_host=None,
        ro_port=9090,
        **kwargs):

        self._user = 'admin'
        self._password = 'admin'
        #self._project = so_project
        self._project = 'admin'
        self._auth_endpoint = '/admin/v1/tokens'
        self._headers = {}

        if len(host.split(':')) > 1:
            # backwards compatible, port provided as part of host
            self._host = host.split(':')[0]
            self._so_port = host.split(':')[1]
        else:
            self._host = host
            self._so_port = so_port

        if ro_host is None:
            ro_host = host
        ro_http_client = http.Http('http://{}:{}/openmano'.format(ro_host, ro_port))
        ro_http_client.set_http_header(
            ['Accept: application/json',
             'Content-Type: application/json'])

        self._http_client = http.Http(
            'https://{}:{}/osm'.format(self._host,self._so_port))
        self._headers['Accept'] = 'application/json'
        self._headers['Content-Type'] = 'application/yaml'
        http_header = ['{}: {}'.format(key,val)
                      for (key,val) in list(self._headers.items())]
        self._http_client.set_http_header(http_header)

        token = self.get_token()
        if not token:
            raise ClientException(
                    'Authentication error: not possible to get auth token')
        self._headers['Authorization'] = 'Bearer {}'.format(token)
        http_header.append('Authorization: Bearer {}'.format(token))
        self._http_client.set_http_header(http_header)

        self.vnfd = vnfd.Vnfd(self._http_client, client=self)
        self.nsd = nsd.Nsd(self._http_client, client=self)
        self.package = package.Package(self._http_client, client=self)
        self.ns = ns.Ns(self._http_client, client=self)
        self.vim = vim.Vim(self._http_client, client=self)
        self.sdnc = sdncontroller.SdnController(self._http_client, client=self)
        self.vnf = vnf.Vnf(self._http_client, client=self)
        '''
        self.vca = vca.Vca(http_client, client=self, **kwargs)
        self.utils = utils.Utils(http_client, **kwargs)
        '''

    def get_token(self):
        postfields_dict = {'username': self._user,
                           'password': self._password,
                           'project-id': self._project}
        http_code, resp = self._http_client.post_cmd(endpoint=self._auth_endpoint,
                              postfields_dict=postfields_dict)
        if http_code not in (200, 201, 202, 204):
            raise ClientException(resp)
        token = json.loads(resp) if resp else None
        if token is not None:
            return token['_id']
        return None

