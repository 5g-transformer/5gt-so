# Copyright 2018 CTTC www.cttc.es
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

"""
File description
"""

# python imports
from logging import getLogger, Formatter, StreamHandler
from logging.handlers import RotatingFileHandler

# project imports


def configure_log(log_file, log_level):
    """
    This function creates the log file if it doesn"t exist and sets the log options.
    Parameters
    ----------
    log_file: string
        Log file name including complete path.
    log_level : string
        One of DEBUG, INFO, WARNING, ERROR or CRITICAL
    Returns
    -------
    None
    """

    # config log
    logger = getLogger("5gtso")
    handler = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=3)

    # log format
    formatter = Formatter("[%(asctime)s.%(msecs).03d] %(levelname)-8s %(message)s", datefmt="%m/%d/%Y %I:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(log_level)

    # for developing, add console log
    ch = StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger.info("Log started, log file %s, log level %s" % (log_file, log_level))
