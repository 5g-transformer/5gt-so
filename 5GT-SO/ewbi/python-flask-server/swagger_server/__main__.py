# Copyright 2019 CTTC www.cttc.es
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from threading import Thread

import connexion
from multiprocessing import set_start_method, Queue
from swagger_server import encoder
from logging import getLogger
from os import path

from monitoring.webhook_receiver_alertmanager_sla import SLAManagerAPI
logger = getLogger("5gtso")



def main():
    logger.info("Starting E/WBI server :)")
    local_swagger_ui_path = path.join(path.dirname(path.realpath(__file__)), 'swagger-ui-cttc')
    options = {'swagger_path': local_swagger_ui_path}
    app = connexion.App(__name__, specification_dir='./swagger/', options=options)
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': '5GT-SO E/WBI'})
    app.add_url_rule("/sla_manager/notifications", view_func=SLAManagerAPI.as_view('SLA Manager'))
    app.run(port=8085, threaded=True)


if __name__ == '__main__':
    main()
