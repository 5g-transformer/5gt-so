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

# python imports
from multiprocessing import Queue, Process
from logging import getLogger
from os import path

# project imports
from log import log

upload_folder = path.realpath(path.join(path.dirname(path.realpath(__file__)), '../upload_packages'))


# process to receive log messages from all processes and send them to the log
def logger_process(log_queue):

    # init log
    log.configure_log("./5gtso.log", "DEBUG")
    logger = getLogger("5gtso")
    logger.info("Log configured")

    # forever get messages and send them to log
    # messages are a list of ["log_level", "message"]
    while True:
        msg = log_queue.get()
        if msg[0] == "DEBUG":
            logger.debug(msg[1])
        elif msg[0] == "INFO":
            logger.info(msg[1])
        elif msg[0] == "WARNING":
            logger.warn(msg[1])
        elif msg[0] == "ERROR":
            logger.error(msg[1])
        elif msg[0] == "CRITICAL":
            logger.error(msg[1])


# instantiate inter-process queue and start logger process
log_queue = Queue()
log_process = Process(target=logger_process, args=(log_queue,))
log_process.start()
