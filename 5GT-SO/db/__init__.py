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
from six.moves.configparser import RawConfigParser

# load db IP port for all db modules
config = RawConfigParser()
config.read("../../db/db.properties")
db_ip = config.get("MongoDB", "db.ip")
db_port = int(config.get("MongoDB", "db.port"))
