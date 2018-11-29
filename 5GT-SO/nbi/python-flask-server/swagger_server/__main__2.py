#!/usr/bin/env python3

# Copyright (C) 2018 CTTC/CERCA
# License: To be defined. Currently use is restricted to partners of the 5G-Transformer project,
#          http://5g-transformer.eu/, no use or redistribution of any kind outside the 5G-Transformer project is
#          allowed.
# Disclaimer: this software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.

import connexion
from multiprocessing import set_start_method, Queue
from swagger_server import encoder
from logging import getLogger
import os

logger = getLogger("5gtso")


def main():
    logger.info("Starting NBI server :)")
    # set_start_method('spawn')
    #local_swagger_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'swagger-ui-cttc')
    local_swagger_path = "./swagger-ui-cttc"

    #options = {'swagger_path': local_swagger_path}
    options = {'swagger_path': local_swagger_path}
    print (local_swagger_path)
    print (os.path.dirname)
    print (os.path.realpath(__file__))
    app = connexion.App(__name__, specification_dir="./swagger/", options=options)
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api("swagger.yaml", arguments={"title": "5GT-SO NBI"})
    app.run(port=8080, threaded=False)


if __name__ == "__main__":
    main()
