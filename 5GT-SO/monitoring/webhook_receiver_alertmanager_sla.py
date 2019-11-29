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

from datetime import timedelta, datetime
import pytz
from flask import request
import json
import iso8601
from db.alert_db import alert_db
from db.ns_db import ns_db
from flask.views import MethodView
from nbi import log_queue
from six.moves.configparser import RawConfigParser
from http.client import HTTPConnection

config = RawConfigParser()
config.read("../../monitoring/monitoring.properties")
so_ip = config.get("ALERTS", "so_scale_ns.ip")
so_port = config.get("ALERTS", "so_scale_ns.port")
so_scale_ns_base_path = config.get("ALERTS", "so_scale_ns.base_path")

class SLAManagerAPI(MethodView):

    def post(self):
        #data_json = request.data
        # data = json.loads(data_json)
        data = request.get_json(force=True)
        alerts = data['alerts']
        for alert in alerts:

            labels = (alert['labels'])
            str_starts_at = str(alert['startsAt'])
            alertname = labels["alertname"]
            log_massage = "Received alert: " + alertname + " startsAt: " + str_starts_at + " status: " + alert['status']
            log_queue.put(["INFO", log_massage])

            if alert['status'] == 'resolved':
                alert_db.set_timestamp(alertname, "")
                continue

            if alert_db.exists_alert_id(alertname):
                if is_problem_resolved(alert) == False:
                    log_queue.put(["DEBUG", "Alert is not resolved= " + alertname + " start date = " + str_starts_at])
                    do_request_for_scaling(alertname)
                continue
            else:
                continue
        return "OK", 200


    def get(self):
        return "200", 200


def is_problem_resolved(alert):
    str_starts_at = str(alert['startsAt'])
    alertname = alert["labels"]["alertname"]
    curent_time = datetime.now(pytz.utc)
    try:
        time_stamp = iso8601.parse_date(alert_db.get_timestamp(alertname))
    except iso8601.iso8601.ParseError:
        log_queue.put(["ERROR", "Error during parse timestamp"])
        time_stamp = datetime.now(pytz.utc)
        alert_db.set_timestamp(alertname, str(datetime.now(pytz.utc)))

    db_alert = alert_db.get_alert(alertname)
    if db_alert == None:
        log_queue.put(["DEBUG", "Alert: " + alertname + " not found in database"])
        return True

    str_timeout = db_alert['cooldownTime']
    timeout = timedelta(seconds=int(str_timeout))
    if curent_time - time_stamp > timeout:
        log_queue.put(["DEBUG", "Timeout unresolved alert = " + alertname + " start date = " + str_starts_at])
        alert_db.set_timestamp(alertname, str(datetime.now(pytz.utc)))
        return False
    else:
        return True


def do_request_for_scaling(alert_id):
    alert = alert_db.get_alert(alert_id)
    ns_id = alert['ns_id']
    ns_status = ns_db.get_ns_status(ns_id)
    current_il = ns_db.get_ns_il(alert['ns_id'])
    rule_actions = alert['ruleActions']
    for rule_action in rule_actions:
        if rule_action['scaleNsToLevelData']['nsInstantiationLevel'] == current_il:
            log_queue.put(["DEBUG", "Current nsInstantiationLevel for nsId: " + ns_id + 'and Alert nsInstantiationLevel is the same'])
            continue
        if ns_status in ["FAILED", "TERMINATED", "INSTANTIATING"]:
            log_queue.put(["DEBUG","Current Status is " + ns_status + " for nsId: " + ns_id ])
            log_queue.put(["DEBUG", "This status is not fit to scaling actions"])
            continue

        log_queue.put(["DEBUG", "Do scaling request for alert: " + alert_id])
        request_to_so_scale_ns(alert)


def request_to_so_scale_ns(alert):
    """
    Parameters
    ----------
    operationId: dict
        Object for creating
    Returns
    -------
    name: type
        return alert
    """

    ns_id = alert['ns_id']
    rule_actions = alert['ruleActions']
    for rule_action in rule_actions:

        scale_request ={
              "scaleType": "SCALE_NS",
              "scaleNsData": {
                "scaleNsToLevelData": {
                  "nsInstantiationLevel": rule_action['scaleNsToLevelData']['nsInstantiationLevel']
                }
              },
              "scaleTime": "0"
            }

        header = {'Content-Type': 'application/json',
                  'Accept': 'application/json'}

        scale_uri = "http://" + so_ip + ":" + so_port + so_scale_ns_base_path + "/" + ns_id + "/scale"

        try:
            conn = HTTPConnection(so_ip, so_port, timeout=10)
            conn.request("PUT", scale_uri, body=json.dumps(scale_request), headers=header)
            rsp = conn.getresponse()
            resources = rsp.read()
            resp_scale = resources.decode("utf-8")
            log_queue.put(["DEBUG", "Request from SO on Scale are:"])
            log_queue.put(["DEBUG", scale_request])
            log_queue.put(["DEBUG", "Response from SO on Scale request are:"])
            log_queue.put(["DEBUG", resp_scale])
            resp_scale = json.loads(resp_scale)
            log_queue.put(["DEBUG", "Response from SO on Scale request are:"])
            log_queue.put(["DEBUG", json.dumps(resp_scale, indent=4)])
            conn.close()
        except ConnectionRefusedError:
            # the SO on Scale request returned wrong response
            log_queue.put(["ERROR", "SO on Scale request returned wrong response"])

