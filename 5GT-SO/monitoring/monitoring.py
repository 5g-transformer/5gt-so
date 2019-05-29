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


"""
File description
"""

# python imports
import copy

from six.moves.configparser import RawConfigParser
from http.client import HTTPConnection
from uuid import uuid4
from json import dumps, loads, load

# project imports
from nbi import log_queue
from db.ns_db import ns_db

# load monitoring configuration manager properties
config = RawConfigParser()
config.read("../../monitoring/monitoring.properties")
monitoring_ip = config.get("MONITORING", "monitoring.ip")
monitoring_port = config.get("MONITORING", "monitoring.port")
monitoring_base_path = config.get("MONITORING", "monitoring.base_path")


########################################################################################################################
# PRIVATE METHODS                                                                                                      #
########################################################################################################################


def get_pm_jobs(nsd, deployed_vnfs_info, nsId):
    """
    Parses the nsd and vnfd descriptors to find possible monitoring jobs
    Parameters
    ----------
    nsd: json 
        Network service descriptor
    deployed_vnfs_info: json 
        dictionary with connection points of the differents vnfs after instantiating
    nsId:
        String with the Network Service Id 
    Returns
    -------
    List 
        List of dictionaries with info of the monitoring jobs
    """
    monitoring_jobs=[]
    if "monitoredInfo" in nsd["nsd"].keys():
        monitored_params = nsd["nsd"]["monitoredInfo"]
        for param in monitored_params:
            vnf = param["monitoringParameter"]["performanceMetric"]
            for sap in deployed_vnfs_info:
                for elem in deployed_vnfs_info[sap]:
                    for key in elem.keys():
                        if (vnf.find(key) !=-1):
                            # this is the vnf that has a external IP to connect and we can establish an exporter
                            pm_job={}
                            pm_job['name']= "NS-"+ nsId +"-VNF-" + key
                            pm_job['address'] = elem[key]
                            pm_job['port'] = 9100 # assuming that it is always a VM exporter
                            pm_job['collectionPeriod'] = 15 # agreed 15 seconds as default
                            pm_job['monitoringParameterId'] = param["monitoringParameter"]["monitoringParameterId"]
                            pm_job['performanceMetric'] = param["monitoringParameter"]["performanceMetric"]
                            pm_job['vnfdId'] = key
                            pm_job['nsId'] = nsId
                            monitoring_jobs.append(pm_job) 
        log_queue.put(["INFO", "monitoring jobs are: %s"% monitoring_jobs]) 
    return monitoring_jobs

def get_pm_jobs_v2(nsd, deployed_vnfs_info, nsId):
    """
    Parses the nsd and vnfd descriptors to find possible monitoring jobs
    Parameters
    ----------
    nsd: json 
        Network service descriptor
    deployed_vnfs_info: json 
        dictionary with connection points of the differents vnfs after instantiating
    nsId:
        String with the Network Service Id 
    Returns
    -------
    List 
        List of dictionaries with info of the monitoring jobs
    """
    monitoring_jobs=[]
    checked_ips = []
    if "monitoredInfo" in nsd["nsd"].keys():
        monitored_params = nsd["nsd"]["monitoredInfo"]
        for param in monitored_params:
            vnf = param["monitoringParameter"]["performanceMetric"]
            # sapINFO: {'videoSap': [{'webserver': '10.0.150.21'}, {'spr21': '10.0.150.3'}], 'mgtSap': [{'spr1': '10.0.150.15'}]}
            for sap in deployed_vnfs_info:
                for elem in deployed_vnfs_info[sap]:
                    for key in elem.keys():
                        if (vnf.find(key) !=-1):
                            if not elem[key] in checked_ips:
                                # this is a new vnf that has a external IP to connect 
                                # and we have to create a new exporter
                                checked_ips.append(elem[key])
                                pm_job={}
                                pm_job['name']= "NS-"+ nsId +"-VNF-" + key
                                pm_job['address'] = elem[key]
                                pm_job['port'] = 9100 # assuming that it is always a VM exporter
                                pm_job['collectionPeriod'] = 15 # agreed 15 seconds as default
                                pm_job['monitoringParameterId'] = []
                                pm_job['performanceMetric'] = []
                                pm_job['monitoringParameterId'].append(param["monitoringParameter"]["monitoringParameterId"])
                                pm_job['performanceMetric'].append(param["monitoringParameter"]["performanceMetric"])
                                pm_job['vnfdId'] = key
                                pm_job['nsId'] = nsId
                                monitoring_jobs.append(pm_job) 
                            else:
                                # this a vnf, that has a pm_job already defined, so you have to update the monitoringParameterId
                                # and performanceMetric element
                                for job in monitoring_jobs:
                                    if (job['address'] == elem[key]):
                                        job['monitoringParameterId'].append(param["monitoringParameter"]["monitoringParameterId"])
                                        job['performanceMetric'].append(param["monitoringParameter"]["performanceMetric"])
        log_queue.put(["DEBUG", "monitoring jobs are: %s"% monitoring_jobs]) 
    return monitoring_jobs

def get_pm_jobs_v2(nsd, deployed_vnfs_info, nsId):
    """
    Parses the nsd and vnfd descriptors to find possible monitoring jobs
    Parameters
    ----------
    nsd: json 
        Network service descriptor
    deployed_vnfs_info: json 
        dictionary with connection points of the differents vnfs after instantiating
    nsId:
        String with the Network Service Id 
    Returns
    -------
    List 
        List of dictionaries with info of the monitoring jobs
    """
    monitoring_jobs=[]
    checked_ips = []
    if "monitoredInfo" in nsd["nsd"].keys():
        monitored_params = nsd["nsd"]["monitoredInfo"]
        for param in monitored_params:
            vnf = param["monitoringParameter"]["performanceMetric"]
            # sapINFO: {'videoSap': [{'webserver': '10.0.150.21'}, {'spr21': '10.0.150.3'}], 'mgtSap': [{'spr1': '10.0.150.15'}]}
            for sap in deployed_vnfs_info:
                for elem in deployed_vnfs_info[sap]:
                    for key in elem.keys():
                        if (vnf.find(key) !=-1):
                            if not elem[key] in checked_ips:
                                # this is a new vnf that has a external IP to connect 
                                # and we have to create a new exporter
                                checked_ips.append(elem[key])
                                pm_job={}
                                pm_job['name']= "NS-"+ nsId +"-VNF-" + key
                                # pm_job['address'] = "http://"+elem[key]
                                pm_job['address'] = elem[key]
                                pm_job['port'] = 9100 # assuming that it is always a VM exporter
                                pm_job['collectionPeriod'] = 15 # agreed 15 seconds as default
                                pm_job['monitoringParameterId'] = []
                                pm_job['performanceMetric'] = []
                                pm_job['monitoringParameterId'].append(param["monitoringParameter"]["monitoringParameterId"])
                                pm_job['performanceMetric'].append(param["monitoringParameter"]["performanceMetric"])
                                pm_job['vnfdId'] = key
                                pm_job['nsId'] = nsId
                                monitoring_jobs.append(pm_job) 
                            else:
                                # this a vnf, that has a pm_job already defined, so you have to update the monitoringParameterId
                                # and performanceMetric element
                                for job in monitoring_jobs:
                                    if (job['address'] == elem[key]):
                                        job['monitoringParameterId'].append(param["monitoringParameter"]["monitoringParameterId"])
                                        job['performanceMetric'].append(param["monitoringParameter"]["performanceMetric"])
        log_queue.put(["DEBUG", "monitoring jobs are: %s"% monitoring_jobs]) 
    return monitoring_jobs

def update_pm_jobs(nsId, deployed_vnfs_info):
    new_jobs = [] # result of scale out operations
    old_jobs = [] # result of scale in operations
    ips_pms = [] # current ips
    current_jobs = ns_db.get_monitoring_info(nsId)
    for job in current_jobs:
        ips_pms.append(job['address'])
    ips_deployed = [] # target ips
    for sap in deployed_vnfs_info:
        for elem in deployed_vnfs_info[sap]:
            for key in elem.keys():
                ips_deployed.append(elem[key])
    # remove old_jobs
    for ip in ips_pms:
        if (ip not in ips_deployed):
            #after scaling this sap is not available
            for job in current_jobs:
                if (job['address'] == ip):
                    old_jobs.append(job['exporterId'])
    # create new_jobs
    for ip in ips_deployed:
        if (ip not in ips_pms):
            # we need to create a new monitoring job
            for sap in deployed_vnfs_info:
                for elem in deployed_vnfs_info[sap]:
                    for key in elem.keys():
                        if(elem[key] == ip):
                            vnf = key
                            for job in current_jobs:
                                if (vnf.find(job['vnfdId']) !=-1):
                                    new_pm_job = copy.deepcopy(job)
                                    new_pm_job['address'] = ip
                                    del new_pm_job['exporterId']
                                    new_jobs.append(new_pm_job)
                                    break
    return [new_jobs, old_jobs]

def configure_monitoring_job(job):
    """
    Contact with the monitoring manager to create info about the different monitoring jobs in the request
    Parameters
    ----------
    job: Dictionary 
        Dictionary with information about the monitoring job to be created
    Returns
    -------
    List
        List of exporter Ids
    """
    # job_id = str(uuid4())
    header = {'Accept': 'application/json',
              'Content-Type': 'application/json'
              }
    # create the exporter for the job
    monitoring_uri = "http://" + monitoring_ip + ":" + monitoring_port + monitoring_base_path + "/exporter"

    body = {"name": job["name"],
            "endpoint": [ {"address": job["address"],
                           "port": job["port"]}
                        ],
            "vnfdId": job["vnfdId"],
            "nsId": job["nsId"],
            "collectionPeriod": job["collectionPeriod"]
           }
    try:
        conn = HTTPConnection(monitoring_ip, monitoring_port)
        conn.request("POST", monitoring_uri, body = dumps(body), headers = header)
        rsp = conn.getresponse()
        exporterInfo = rsp.read()
        exporterInfo = exporterInfo.decode("utf-8")
        exporterInfo = loads(exporterInfo)
        log_queue.put(["INFO", "Deployed exporter info is:"])
        log_queue.put(["INFO", dumps(exporterInfo, indent = 4)])
    except ConnectionRefusedError:
        log_queue.put(["ERROR", "the Monitoring platform is not running or the connection configuration is wrong"])
    job['exporterId'] = exporterInfo["exporterId"]
    return job

def get_dashboard_query(pm, exporterId):
    """
    generate the string to make the prometheus query when creating a dashboard
    Parameters
    ----------
    pm: string
        String with the type of performanceNetwork Service Id
    exporterId:
        String with the exporter Id
    # query: string
    #    Query to show in the dashboard
    Returns
    -------
    Prometheusquery
        string with the prometheus query
    """
    Prometheusquery = ""
    # pm's can be:
                  # VcpuUsageMean.<vnfdId>
                  # VmemoryUsageMean.<vnfdId>
                  # VdiskUsageMean.<vnfdId>
                  # ByteIncoming.<vnfdId>.<vnfExtCpdId>
    if (pm.find("cpu") !=-1):
        Prometheusquery = "sum without (cpu, mode) (rate(node_cpu_seconds_total{mode!=" + "\"idle\"" + ", job=\"" + exporterId + "\"}[1m]))*100"      
    if (pm.find("memory") !=-1):
        Prometheusquery =  "((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100), {job= \"" + exporterId +"\"}"
    if (pm.find("disk") !=-1):
        Prometheusquery = "((node_filesystem_avail_bytes{mountpoint=" + "\/""} / node_filesystem_size_bytes{mountpoint=" + "\/""}) * 100), {job= \"" + exporterId +"\"}"
    if (pm.find("Byte") !=-1):
        port = pm.split(".")[2]
        Prometheusquery = "rate(node_network_receive_bytes_total{device=" + "\"" + port + "\"" + ",job=\"" + exporterId + "\"}[1m])"
    return Prometheusquery


def get_dashboard_query_v2(nsId, vnfdId, pm):
    """
    generate the string to make the prometheus query when creating a dashboard
    Parameters
    ----------
    pm: string
        String with the type of performanceNetwork Service Id
    exporterId:
        String with the exporter Id
    # query: string
    #    Query to show in the dashboard
    Returns
    -------
    Prometheusquery
        string with the prometheus query
    """
    Prometheusquery = ""
    if (pm.find("cpu") !=-1):
        Prometheusquery = "avg((1 - avg by(instance) (irate(node_cpu_seconds_total{mode=\"idle\",nsId=\"" + nsId + "\",vnfdId=\"" + vnfdId + "\"}[1m]))) * 100)"
    if (pm.find("memory") !=-1):
        Prometheusquery =  "avg by (vnfdId)(((node_memory_MemTotal_bytes{nsId=\"" + nsId + "\",vnfdId=\"" + vnfdId + "\"} - node_memory_MemFree_bytes{nsId=\"" + nsId + "\",vnfdId=\"" + vnfdId + "\"}) / node_memory_MemTotal_bytes{nsId=\"" + nsId + "\",vnfdId=\"" + vnfdId + "\"}) * 100)"
    if (pm.find("disk") !=-1):
        Prometheusquery = "((node_filesystem_size_bytes{fstype=~\"ext4|vfat\", nsId=\"" + nsId + "\",vnfdId=\"" + vnfdId + "\"} - node_filesystem_free_bytes{fstype=~\"ext4|vfat\", nsId=\"" + nsId + "\", vnfdId=\"" + vnfdId + "\"}) / node_filesystem_size_bytes{fstype=~\"ext4|vfat\", nsId=\"" + nsId + "\",vnfdId=\"" + vnfdId + "\"}) * 100"
    if (pm.find("Byte") !=-1):
        port = pm.split(".")[2]
        Prometheusquery = "rate(node_network_receive_bytes_total{device=\"" + port + "\",nsId=\"" + nsId + "\",vnfdId=\"" + vnfdId + "\"}[1m])"
    return Prometheusquery


def configure_dashboard(nsId, jobs):
    """
    Contact with the monitoring manager to create the dashboard with query
    Parameters
    ----------
    nsId: string 
        String with the Network Service Id 
    jobs:
        Array of dictionaries with job information
    Returns
    -------
    Dictionary
        Dashboard Id and url
    """
    if (len(jobs) == 0):
        return {}
    else:
        header = {'Content-Type': 'application/json',
                  'Accept': 'application/json'}
        # create the exporter for the job
        monitoring_uri = "http://" + monitoring_ip + ":" + monitoring_port + monitoring_base_path + "/dashboard"
        body = {"name": "NS_" + nsId,
                "panels": [],
                "users": [nsId], 
                "plottedTime": 60,
                "refreshTime": "5s"
               }
        for job in jobs:
            panel = {}
            panel['title'] = job["monitoringParameterId"] + "(" + job["performanceMetric"] + ")"
            panel['query'] = get_dashboard_query(job['performanceMetric'], job['exporterId'])
            panel['size'] = ""
            body['panels'].append(panel)
        try:
            conn = HTTPConnection(monitoring_ip, monitoring_port)
            conn.request("POST", monitoring_uri, dumps(body), header)
            rsp = conn.getresponse()
            dashboardInfo = rsp.read()
            dashboardInfo = dashboardInfo.decode("utf-8")
            dashboardInfo = loads(dashboardInfo)
            log_queue.put(["INFO", "deployed Dashboard info is:"])
            dashboardInfo['url'] = "http://" + monitoring_ip + ":3000" + dashboardInfo['url']
            log_queue.put(["INFO", dumps(dashboardInfo, indent = 4)])
        except ConnectionRefusedError:
            log_queue.put(["ERROR", "the Monitoring platform is not running or the connection configuration is wrong"])
        return {"dashboardId" : dashboardInfo["dashboardId"],
                "dashboardUrl" : dashboardInfo["url"] }

def configure_dashboard_v2(nsId, jobs):
    """
    Contact with the monitoring manager to create the dashboard with query
    Parameters
    ----------
    nsId: string 
        String with the Network Service Id 
    jobs:
        Array of dictionaries with job information
    Returns
    -------
    Dictionary
        Dashboard Id and url
    """
    if (len(jobs) == 0):
        return {}
    else:
        header = {'Content-Type': 'application/json',
                  'Accept': 'application/json'}
        # create the exporter for the job 
        monitoring_uri = "http://" + monitoring_ip + ":" + monitoring_port + monitoring_base_path + "/dashboard"
        body = {"name": "NS_" + nsId,
                "panels": [],
                "users": [nsId], 
                "plottedTime": 60,
                "refreshTime": "5s"
               }
        #checking the different labels of the exporters for a network service
        vnfIds = []
        for job in jobs:
            if job['vnfdId'] not in vnfIds:
                # in case there are two instances of the same exporter you make the average
                vnfIds.append(job)
        for job in vnfIds:
            for metric in range(0, len(job["performanceMetric"])):
               panel = {}
               panel['title'] = job["monitoringParameterId"][metric] + "(" + job["performanceMetric"][metric] + ")"
               panel['query'] = get_dashboard_query_v2(job['nsId'], job['vnfdId'], job['performanceMetric'][metric])
               panel['size'] = ""
               body['panels'].append(panel)
        try:
            conn = HTTPConnection(monitoring_ip, monitoring_port)
            conn.request("POST", monitoring_uri, dumps(body), header)
            rsp = conn.getresponse()
            dashboardInfo = rsp.read()
            dashboardInfo = dashboardInfo.decode("utf-8")
            dashboardInfo = loads(dashboardInfo)
            log_queue.put(["INFO", "deployed Dashboard info is:"])
            dashboardInfo['url'] = "http://" + monitoring_ip + ":3000" + dashboardInfo['url']
            log_queue.put(["INFO", dumps(dashboardInfo, indent = 4)])
        except ConnectionRefusedError:
                log_queue.put(["ERROR", "the Monitoring platform is not running or the connection configuration is wrong"])
        return {"dashboardId" : dashboardInfo["dashboardId"],
                "dashboardUrl" : dashboardInfo["url"] }

def update_dashboard(nsId, jobs, current_dashboardInfo):
    """
    Contact with the monitoring manager to upadte the dashboard with query
    Parameters
    ----------
    nsId: string
        String with the Network Service Id
    jobs:
        Array of dictionaries with job information
    Returns
    -------
    Dictionary
        Dashboard Id and url
    """
    if (len(jobs) == 0):
        return {}
    else:
        header = {'Content-Type': 'application/json',
                  'Accept': 'application/json'}
        # create the exporter for the job
        monitoring_uri = "http://" + monitoring_ip + ":" + monitoring_port + monitoring_base_path + "/dashboard/" + current_dashboardInfo["dashboardId"]
        body = {"dashboardId": current_dashboardInfo["dashboardId"],
                "url": current_dashboardInfo["dashboardUrl"].replace("http://" + monitoring_ip + ":3000",""),
                "name": "NS_" + nsId,
                "panels": [],
                "users": [nsId],
                "plottedTime": 60,
                "refreshTime": "5s"
               }
        #checking the different labels of the exporters for a network service
        vnfIds = []
        for job in jobs:
            if job['vnfdId'] not in vnfIds:
                vnfIds.append(job)
        for job in vnfIds:
            for metric in range(0, len(job["performanceMetric"])):
               panel = {}
               panel['title'] = job["monitoringParameterId"][metric] + "(" + job["performanceMetric"][metric] + ")"
               panel['query'] = get_dashboard_query_v2(job['nsId'], job['vnfdId'], job['performanceMetric'][metric])
               # panel['size'] = "fullscreen"
               panel['size'] = ""
               body['panels'].append(panel)
        try:
            conn = HTTPConnection(monitoring_ip, monitoring_port)
            conn.request("PUT", monitoring_uri, dumps(body), header)
            rsp = conn.getresponse()
            dashboardInfo = rsp.read()
            dashboardInfo = dashboardInfo.decode("utf-8")
            dashboardInfo = loads(dashboardInfo)
            log_queue.put(["DEBUG", "deployed Dashboard info is:"])
            dashboardInfo['url'] = "http://" + monitoring_ip + ":3000" + dashboardInfo['url']
            log_queue.put(["DEBUG", dumps(dashboardInfo, indent = 4)])
        except ConnectionRefusedError:
                log_queue.put(["ERROR", "the Monitoring platform is not running or the connection configuration is wrong"])
        return {"dashboardId" : dashboardInfo["dashboardId"],
                "dashboardUrl" : dashboardInfo["url"] }

def stop_monitoring_job(jobId):
    """
    Contact with the monitoring manager to stop the requested exporter
    Parameters
    ----------
    dashboardId: string 
        String identifying the dashboard to be removed 
    Returns
    -------
    None
    """
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    # create the exporter for the job 
    monitoring_uri = "http://" + monitoring_ip + ":" + monitoring_port + monitoring_base_path + "/exporter"
    try:
        conn = HTTPConnection(monitoring_ip, monitoring_port)
        conn.request("DELETE", monitoring_uri + "/" + jobId, None, header)
        rsp = conn.getresponse()
    except ConnectionRefusedError:
        log_queue.put(["ERROR", "the Monitoring platform is not running or the connection configuration is wrong"])

def stop_dashboard(dashboardId):
    """
    Contact with the monitoring manager to stop the dashboard
    Parameters
    ----------
    dashboardId: string 
        String identifying the dashboard to be removed 
    Returns
    -------
    None
    """
    header = {'Content-Type': 'application/json',
              'Accept': 'application/json'}
    # create the exporter for the job 
    monitoring_uri = "http://" + monitoring_ip + ":" + monitoring_port + monitoring_base_path + "/dashboard"
    try:
        conn = HTTPConnection(monitoring_ip, monitoring_port)
        conn.request("DELETE", monitoring_uri + "/" + dashboardId, None, header)
        rsp = conn.getresponse()
    except ConnectionRefusedError:
        log_queue.put(["ERROR", "the Monitoring platform is not running or the connection configuration is wrong"])


########################################################################################################################
# PUBLIC METHODS                                                                                                       #
########################################################################################################################


def configure_ns_monitoring(nsId, nsd, vnfds, deployed_vnfs_info):
    """
    Contact with the monitoring manager to configure the monitoring jobs and the dashboard
    Parameters
    ----------
    nsId: string 
        String identifying the network service
    nsd: json
        Network service descriptor
    vnfds: json
        VNF descriptor
    deployed_vnfs_info: dict
        Dictionary with information of the saps of the deployed vnfs in a network service
    Returns
    -------
    None
    """
    # parse NSD / VNFDs to get the list of monitoring jobs to be configured and its information
    # ! we need the input of the vnfds, to have the endpoints!
    jobs = get_pm_jobs_v2(nsd, deployed_vnfs_info, nsId)
    # for each job request the Monitoring Configuration Manager to configure the job and save the job_id
    job_ids = []
    for job in jobs:
        job_elem = configure_monitoring_job(job)
        job_ids.append(job_elem)
    # save the list of jobs in the database
    ns_db.set_monitoring_info(nsId, job_ids)
    # create the dashboard for the monitoring jobs
    dashboard_id = configure_dashboard_v2(nsId, jobs)
    ns_db.set_dashboard_info(nsId, dashboard_id)

def update_ns_monitoring(nsId, nsd, vnfds, deployed_vnfs_info):
    """
    Contact with the monitoring manager to update the monitoring jobs and the dashboard
    Parameters
    ----------
    nsId: string 
        String identifying the network service
    nsd: json
        Network service descriptor
    vnfds: json
        VNF descriptor
    deployed_vnfs_info: dict
        Dictionary with information of the saps of the deployed vnfs in a network service
    Returns
    -------
    None
    """
    new_jobs = [] # result of scale out operations
    old_jobs = [] # result of scale in operations
    job_ids = []
    [new_jobs, old_jobs] = update_pm_jobs(nsId, deployed_vnfs_info)
    for job in new_jobs:
        job_elem = configure_monitoring_job(job)
        job_ids.append(job_elem)
    # update the list of jobs in the database
    for job in old_jobs:
        stop_monitoring_job(job)
    ns_db.update_monitoring_info(nsId, job_ids, old_jobs)
    # update the dashboard for the monitoring jobs: once all required ones have been created or erased
    # jobs = ns_db.get_monitoring_info(nsId)
    # dashboard_info = ns_db.get_dashboard_info(nsId)
    # if "dashboardId" in dashboard_info.keys():
    #     stop_dashboard(dashboard_info["dashboardId"])
    # dashboard_id = configure_dashboard_v2(nsId, jobs)
    # we rewrite the dasboard info
    # ns_db.set_dashboard_info(nsId, dashboard_id)
   

def stop_ns_monitoring(nsId):
    """
    Contact with the monitoring manager to delete the monitoring jobs and the dashboard
    Parameters
    ----------
    nsId: string 
        String identifying the network service
    Returns
    -------
    None
    """
    # parse NSD / VNFDs to get the list of montoring jobs to be configured and its information
    job_ids = ns_db.get_monitoring_info(nsId)
    for job_id in job_ids:
        stop_monitoring_job(job_id['exporterId'])
    # delete monitor jobs from database by posting an empty list
    ns_db.set_monitoring_info(nsId, [])
    dashboard_info = ns_db.get_dashboard_info(nsId)
    if "dashboardId" in dashboard_info.keys():
        stop_dashboard(dashboard_info["dashboardId"])
        ns_db.set_dashboard_info(nsId, {})
