# Author: Inaki Pascual
# Copyright (C) 2018 CTTC/CERCA
# License: To be defined. Currently use is restricted to partners of the 5G-Transformer project,
#          http://5g-transformer.eu/, no use or redistribution of any kind outside the 5G-Transformer project is
#          allowed.
# Disclaimer: this software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.

"""
File description
"""

# python imports

# project imports


def error400(message):
    return {"message": message,
            "status": 400,
            "type": "Bad Request"
            }, 400


def error404(message):
    return {"message": message,
            "status": 404,
            "type": "Not found"
            }, 404
