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

# python imports
import traceback
from http.client import HTTPConnection
from six.moves.configparser import RawConfigParser
import json
# project imports
from nbi import log_queue
from db.ns_db import ns_db
from db.alert_db import alert_db

# load monitoring configuration sla manager properties
config = RawConfigParser()
config.read("../../monitoring/monitoring.properties")
monitoring_platform_ip = config.get("ALERTS", "monitoring_platform.ip")
monitoring_platform_port = config.get("ALERTS", "monitoring_platform.port")
monitoring_platform_base_path = config.get("ALERTS", "monitoring_platform.base_path")
alert_target = config.get("ALERTS", "monitoring_platform.alert_target")
expressions = dict(config.items("EXPRESSIONS"))


########################################################################################################################
# PRIVATE METHODS                                                                                                      #
########################################################################################################################


def get_pm_alerts(nsd, deployed_vnfs_info, ns_id):
    """
    Parses the nsd and vnfd descriptors to find possible alerts jobs
    Parameters
    ----------
    nsd: json
        Network service descriptor
    deployed_vnfs_info: json
        dictionary with connection points of the differents vnfs after instantiating
    ns_id:
        String with the Network Service Id
    Returns
    -------
    List
        List of dictionaries with info of the monitoring jobs
    """
    alerts = []
    if "autoScalingRule" in nsd["nsd"].keys():
        auto_scaling_rules = nsd["nsd"]["autoScalingRule"]
        monitored_infos = nsd["nsd"]["monitoredInfo"]
        monitoring_jobs = ns_db.get_monitoring_info(ns_id)


        for auto_scaling_rule in auto_scaling_rules:
            summury_alert_query = ""
            scaling_criterias = auto_scaling_rule['ruleCondition']['scalingCriteria']
            # detect OperationType
            scaling_operation = "OR"
            if 'scaleInOperationType' in auto_scaling_rule:
                scaling_operation = auto_scaling_rule['scaleInOperationType']
            if 'scaleOutOperationType' in auto_scaling_rule:
                scaling_operation = auto_scaling_rule['scaleOutOperationType']

            # parsing scalingCriteria
            for idx_scaling_criterias, scaling_criteria in enumerate(scaling_criterias):
                pm_alert = {}
                # mapping between autoScalingRule -> ruleCondition -> scalingCriteria -> nsMonitoringParamRef and
                # ns -> monitoring_jobs -> monitoringParameterId
                # get nsMonitoringParamRef
                ns_monitoring_param_ref = scaling_criteria['nsMonitoringParamRef']
                performance_metric = ""
                alert_metric = ""
                index_monitor_parameter = -1
                # Get monitored job id from ns
                for idx, monitoring_job in enumerate(monitoring_jobs):
                    if ns_monitoring_param_ref in monitoring_job['monitoringParameterId']:
                        idx_in_monitoring_parameter_id = monitoring_job['monitoringParameterId'].index(ns_monitoring_param_ref)
                        index_monitor_parameter = idx
                        performance_metric = monitoring_job['performanceMetric'][idx_in_monitoring_parameter_id]
                        break

                # Error if Alert parameter wasn't found between monitored parameters
                if index_monitor_parameter == -1:
                    exception_msg = "Alert parameter " + ns_monitoring_param_ref + " is not found in monitored parameters"
                    log_queue.put(["ERROR", exception_msg])
                    raise Exception(exception_msg)

                monitoring_job = monitoring_jobs[index_monitor_parameter]
                # convert expression from IFA to PQL
                alert_query = convert_expresion(performance_metric, monitoring_job['exporterId'], ns_id, monitoring_job['vnfdId'])


                # Creating summary query for request
                if (idx_scaling_criterias == 0) and (len(scaling_criterias) == 1):
                    summury_alert_query = alert_query

                if (idx_scaling_criterias != (len(scaling_criterias) - 1)) and (len(scaling_criterias) > 1):
                    summury_alert_query = summury_alert_query + "(" + alert_query + ") " + scaling_operation + " "

                if (idx_scaling_criterias == (len(scaling_criterias) - 1)) and (len(scaling_criterias) > 1):
                    summury_alert_query = summury_alert_query + "(" + alert_query + ")"

            # collect information for ALERT database and for requests for alert creating
            pm_alert['rule_id'] = auto_scaling_rule['ruleId']
            pm_alert['query'] = summury_alert_query
            pm_alert['label'] = "label"
            pm_alert['severity'] = "warning"
            if 'scaleOutThreshold' in scaling_criteria:
                pm_alert['value'] = scaling_criteria['scaleOutThreshold']
            if 'scaleInThreshold' in scaling_criteria:
                pm_alert['value'] = scaling_criteria['scaleInThreshold']
            if 'scaleOutRelationalOperation' in scaling_criteria:
                pm_alert['kind'] = scaling_criteria['scaleOutRelationalOperation']
            if 'scaleInRelationalOperation' in scaling_criteria:
                pm_alert['kind'] = scaling_criteria['scaleInRelationalOperation']
            try:
                pm_alert['kind'] = convert_relational_operation_from_nsd_to_monitoring_platform(pm_alert['kind'])
            except KeyError as e:
                exception_msg = "Relation operation value for rule " + pm_alert['rule_id'] + " + has wrong format"
                log_queue.put(["ERROR", exception_msg])
                raise Exception(exception_msg)

            pm_alert['enabled'] = auto_scaling_rule['ruleCondition']['enabled']
            pm_alert['cooldownTime'] = auto_scaling_rule['ruleCondition']['cooldownTime']
            pm_alert['thresholdTime'] = auto_scaling_rule['ruleCondition']['thresholdTime']
            pm_alert['target'] = alert_target
            pm_alert['ruleActions'] = auto_scaling_rule['ruleActions']
            alerts.append(pm_alert)
    return alerts

def convert_relational_operation_from_nsd_to_monitoring_platform(operation):
    # this method convert relation operation from NSD format to monitoring platform format
    map_translation = {}
    map_translation['GT'] = 'G'
    map_translation['GE'] = 'GEQ'
    map_translation['LT'] = 'L'
    map_translation['LE'] = 'LEQ'
    map_translation['EQ'] = 'EQ'
    map_translation['NEQ'] = 'NEQ'

    monitoring_platform_operation = map_translation[operation]

    return monitoring_platform_operation

def convert_expresion(performance_metric, job_id, ns_id, vnfd_id):
    performance_metric_parts = performance_metric.split(".")
    try:
        return_expresion = expressions[(performance_metric_parts[0].lower())]
    except KeyError as er:
        exception_msg = "Error to create expressions for the Monitoring platform \n"
        exception_msg += "Can't find key expressions for " + str(er)
        log_queue.put(["ERROR", exception_msg])
        raise Exception(exception_msg)
    return_expresion = return_expresion.replace("{job_id}", 'job="' + str(job_id) + '"')
    return_expresion = return_expresion.replace("{nsId}", 'nsId="' + str(ns_id) + '"')
    return_expresion = return_expresion.replace("{vnfdId}", 'vnfdId="' + str(vnfd_id) + '"')
    if performance_metric_parts[0] == "ByteIncoming":
        return_expresion = return_expresion.replace("{port}", 'device="' + str(performance_metric_parts[2]) + '"')
    return return_expresion


def get_alerts():
    """
    Parameters
    ----------
    Returns
    -------
    name: type
        return alerts
    """
    header = {'Accept': 'application/json'}
    monitoring_uri = "http://" + monitoring_platform_ip + ":" + monitoring_platform_port + monitoring_platform_base_path + "/alert"
    try:
        conn = HTTPConnection(monitoring_platform_ip, monitoring_platform_port)
        conn.request("GET", monitoring_uri, None, header)
        rsp = conn.getresponse()
        resources = rsp.read()
        alerts = resources.decode("utf-8")
        log_queue.put(["DEBUG", "Alerts from Config Manager are:"])
        log_queue.put(["DEBUG", alerts])
        alerts = json.loads(alerts)
        log_queue.put(["DEBUG", "Alerts from Config Manager are:"])
        log_queue.put(["DEBUG", json.dumps(alerts, indent=4)])
        conn.close()
    except ConnectionRefusedError:
        # the Config Manager is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the Config Manager is not running or the connection configuration is wrong"])
    return alerts


def get_alert(alert_id):
    """
    Parameters
    ----------
    Returns
    -------
    name: type
        return alert
    """
    header = {'Accept': 'application/json'}
    monitoring_uri = "http://" + monitoring_platform_ip + ":" + monitoring_platform_port + monitoring_platform_base_path + "/alert/" + str(
        alert_id)
    try:
        conn = HTTPConnection(monitoring_platform_ip, monitoring_platform_port)
        conn.request("GET", monitoring_uri, None, header)
        rsp = conn.getresponse()
        resources = rsp.read()
        alert = resources.decode("utf-8")
        log_queue.put(["DEBUG", "Alerts from Config Manager are:"])
        log_queue.put(["DEBUG", alert])
        alert = json.loads(alert)
        log_queue.put(["DEBUG", "Alerts from Config Manager are:"])
        log_queue.put(["DEBUG", json.dumps(alert, indent=4)])
        conn.close()
    except ConnectionRefusedError:
        # the Config Manager is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the Config Manager is not running or the connection configuration is wrong"])
    return alert


def create_alert(alert):
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
    header = {'Accept': 'application/json',
              'Content-Type': 'application/json'
              }
    monitoring_uri = "http://" + monitoring_platform_ip + ":" + monitoring_platform_port + monitoring_platform_base_path + "/alert"
    try:
        conn = HTTPConnection(monitoring_platform_ip, monitoring_platform_port)
        conn.request("POST", monitoring_uri, body=json.dumps(alert), headers=header)
        rsp = conn.getresponse()
        resources = rsp.read()
        resp_alert = resources.decode("utf-8")
        log_queue.put(["DEBUG", "Alert from Config Manager are:"])
        log_queue.put(["DEBUG", resp_alert])
        resp_alert = json.loads(resp_alert)
        log_queue.put(["DEBUG", "Alert from Config Manager are:"])
        log_queue.put(["DEBUG", json.dumps(resp_alert, indent=4)])
        conn.close()
    except ConnectionRefusedError:
        # the Config Manager is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the Config Manager is not running or the connection configuration is wrong"])
    return resp_alert


def update_alert(alert):
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
    header = {'Accept': 'application/json',
              'Content-Type': 'application/json'
              }
    monitoring_uri = "http://" + monitoring_platform_ip + ":" + monitoring_platform_port + monitoring_platform_base_path + "/alert/" + str(
        alert['alertId'])
    print(monitoring_uri)
    try:
        conn = HTTPConnection(monitoring_platform_ip, monitoring_platform_port)
        conn.request("PUT", monitoring_uri, body=json.dumps(alert), headers=header)
        rsp = conn.getresponse()
        resources = rsp.read()
        resp_alert = resources.decode("utf-8")
        log_queue.put(["DEBUG", "Alert from Config Manager are:"])
        log_queue.put(["DEBUG", resp_alert])
        resp_alert = json.loads(resp_alert)
        log_queue.put(["DEBUG", "Alert from Config Manager are:"])
        log_queue.put(["DEBUG", json.dumps(resp_alert, indent=4)])
        conn.close()
    except ConnectionRefusedError:
        # the Config Manager is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the Config Manager is not running or the connection configuration is wrong"])
    return resp_alert


def delete_alert(alert_id):
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
    header = {'Accept': 'application/json'
              }
    monitoring_uri = "http://" + monitoring_platform_ip + ":" + monitoring_platform_port + monitoring_platform_base_path + "/alert/" + str(
        alert_id)
    try:
        conn = HTTPConnection(monitoring_platform_ip, monitoring_platform_port)
        conn.request("DELETE", monitoring_uri, headers=header)
        rsp = conn.getresponse()
        resources = rsp.read()
        resp_alert = resources.decode("utf-8")
        log_queue.put(["DEBUG", "Alert from Config Manager are:"])
        log_queue.put(["DEBUG", resp_alert])
        resp_alert = json.loads(resp_alert)
        log_queue.put(["DEBUG", "Alert from Config Manager are:"])
        log_queue.put(["DEBUG", json.dumps(resp_alert, indent=4)])
        conn.close()
    except ConnectionRefusedError:
        # the Config Manager is not running or the connection configuration is wrong
        log_queue.put(["ERROR", "the Config Manager is not running or the connection configuration is wrong"])


def configure_ns_alerts(nsId, nsdId, nsd, vnfds, deployed_vnfs_info):
    """
    """
    # parse NSD / VNFDs to get the list of monitoring jobs to be configured and its information
    # ! we need the input of the vnfds, to have the endpoints!
    alerts_dict = {}
    alert_db_entity = {}
    alerts = get_pm_alerts(nsd, deployed_vnfs_info, nsId)
    # for each job request the Monitoring Configuration Manager to configure the alert and save the alert_id
    for alert_idx, alert in enumerate(alerts):
        alert_request = {
            "alertName": alert['rule_id'],
            'query': alert['query'],
            "labels": [
                # {
                #     "key": "string",
                #     "value": "string"
                # }
            ],
            'severity': alert['severity'],
            'value': alert['value'],
            'kind': alert['kind'],
            'for': str(alert['thresholdTime']) + "s",
            'target': alert['target']
        }
        result_alert = create_alert(alert_request)
        # send alert request
        alert_id = result_alert['alertId']
        alerts[alert_idx].update({'alertId': alert_id})
        alerts[alert_idx].update({'nsId': nsId})
        alerts_dict[alert_id] = alerts[alert_idx]
        # create object to save in db alerts
        alert_db_entity = {}
        alert_db_entity['alert_id'] = alert_id
        alert_db_entity['status'] = ""
        alert_db_entity['nsd_id'] = nsdId
        alert_db_entity['ns_id'] = nsId
        alert_db_entity['rule_id'] = alert['rule_id']
        alert_db_entity['thresholdTime'] = alert['thresholdTime']
        alert_db_entity['cooldownTime'] = alert['cooldownTime']
        alert_db_entity['enabled'] = alert['enabled']
        alert_db_entity['ruleActions'] = alert['ruleActions']
        alert_db_entity['target'] = alert['target']
        alert_db_entity['timestamp'] = ""
        alert_db.create_alert_record(alert_db_entity)
    # save the list of alerts in the database
    ns_db.set_alert_info(nsId, alerts_dict)


def delete_ns_alerts(nsId):
    """
    """
    # parse NSD / VNFDs to get the list of alerts to be configured and its information
    alerts = ns_db.get_alerts_info(nsId)
    for alert in alerts:
        delete_alert(alert)
    # delete monitor jobs from database by posting an empty list
    ns_db.set_alert_info(nsId, [])
