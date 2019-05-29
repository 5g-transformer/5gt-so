import copy
import sys

print("hola")
nsId = "fgt-4f5d2fe-b6a6-4386-92d4-4192a7146f07"
vnfdId = "spr21"
port = "eth2"
# VcpuUsageMean=avg((1 - avg by (instance) (irate(node_cpu_seconds_total{{nsId}, {vnfdId}, mode="idle"}[1m])))*100) 
Prometheusquery = "avg((1 - avg by (instance) (irate(node_cpu_seconds_total{{" + nsId + "},{" + vnfdId + "},mode=\"" + "idle\"" + "}[1m])))*100)" 
Prometheusquery =  "avg by (instance) ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100), {{" + nsId + "},{" + vnfdId + "}}"
Prometheusquery = "avg by (instance) ((node_filesystem_avail_bytes{mountpoint=" + "\/""} / node_filesystem_size_bytes{mountpoint=" + "\/""}) * 100), {{" + nsId + "},{" + vnfdId + "}}"
Prometheusquery = "avg by (instance) (rate(node_network_receive_bytes_total{device=" + "\"" + port + "\"" + ",{" + nsId + "},{" + vnfdId + "}}[1m]))"
print("la query: ", Prometheusquery)
sys.exit(-1)



deployed_vnfs_info={'videoSap': [{'webserver': '10.0.150.21'}, {'spr21': '10.0.150.3'}, {'spr21-2':'10.0.150.25'}], 'mgtSap': [{'spr1': '10.0.150.15'}]}

#for sap in sapINFO:
#    print("el sap es: ", sap)
#    for elem in sapINFO[sap]:
#        print ("el elem es: ", elem)
#        for key in elem.keys():
#            if (key == "webserver"):
#                print("ip: ", elem[key])

# deployed_vnfs_info: {'videoSap': [{'webserver': '10.11.12.14'}, {'spr21': '10.11.12.5'}, {'spr21': '10.11.12.7'}], 'mgtSap': [{'spr1': '10.20.30.6'}]}
new_jobs = [] # result of scale out operations
old_jobs = [] # result of scale in operations
#ips_pms = ['10.0.150.13','10.0.150.21','10.0.150.3'] # current ips
ips_pms = []
current_jobs = [ { "collectionPeriod" : 15, "exporterId" : "fb67c8e4-9ab7-47a0-9670-ed80d8630d2b", "address" : "10.0.150.3", "port" : 9100, "name" : "NS-fgt-4f5d2fe-b6a6-4386-92d4-4192a7146f07-VNF-spr21", "nsId" : "fgt-4f5d2fe-b6a6-4386-92d4-4192a7146f07", "performanceMetric" : "VcpuUsageMean.spr21", "vnfdId" : "spr21", "monitoringParameterId" : "mp1" }, { "collectionPeriod" : 15, "exporterId" : "fb67c8e4-9ab7-47a0-9670-ed80d8655555", "address" : "10.0.150.13", "port" : 9100, "name" : "NS-fgt-4f5d2fe-b6a6-4386-92d4-4192a7146f07-VNF-spr21", "nsId" : "fgt-4f5d2fe-b6a6-4386-92d4-4192a7146f07", "performanceMetric" : "VcpuUsageMean.spr21", "vnfdId" : "spr21", "monitoringParameterId" : "mp1" }, { "collectionPeriod" : 15, "exporterId" : "069f3107-105b-4ada-bbc4-a9b7ff8f5b4c", "address" : "10.0.150.21", "port" : 9100, "name" : "NS-fgt-4f5d2fe-b6a6-4386-92d4-4192a7146f07-VNF-webserver", "nsId" : "fgt-4f5d2fe-b6a6-4386-92d4-4192a7146f07", "performanceMetric" : "VcpuUsageMean.webserver", "vnfdId" : "webserver", "monitoringParameterId" : "mp2" } ]
for job in current_jobs:
    ips_pms.append(job['address'])
print ("ips pms: ", ips_pms)
ips_deployed = [] # target ips
for sap in deployed_vnfs_info:
    for elem in deployed_vnfs_info[sap]:
        for key in elem.keys():
            ips_deployed.append(elem[key])
print ("ips_deployed: ", ips_deployed)
# remove old_jobs
for ip in ips_pms:
    if (ip not in ips_deployed):
        #after scaling this sap is not available
        for job in current_jobs:
            if (job['address'] == ip):
                old_jobs.append(job['exporterId'])
print ("old_jobs: ", old_jobs)
# create new_jobs
for ip in ips_deployed:
    if (ip not in ips_pms):
        # we need to create a new monitoring job
        print ("la ip que no esta en ip_pms es: ", ip)
        for sap in deployed_vnfs_info:
            for elem in deployed_vnfs_info[sap]:
                for key in elem.keys():
                    if(elem[key] == ip):
                        vnf = key
                        print ("la vnf es: ", vnf)
                        for job in current_jobs:
                            if (vnf.find(job['vnfdId']) !=-1):
                                print ("el job es: ", job)
                                new_pm_job = copy.deepcopy(job)
                                new_pm_job['address'] = ip
                                del new_pm_job['exporterId']
                                new_jobs.append(new_pm_job)
                                break
print ("new_jobs: ", new_jobs)



