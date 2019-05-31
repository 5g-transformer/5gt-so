import random
from operator import itemgetter

selectedDst=[]
single={}
coupled={}
radius=0.0
latitude=0.0
longitude=0.0
cpu=0
ram=0
storage=0
max_latency=0
required_capacity=0
AVcpu=0
AVram=0
AVstorage=0
allocated={}
tempAlloc={}
selected=[]
mapped=[]
VirtualLinks=[]
selectedDst=False
totalLatency=0.0
mec=False

# -totalcost va nella risp anche se non lo considero?

def PALat(NFVIPOP,LLs,NSD):
	global nfviId, totalLatency, selected, selectedDst, allocated
	allocated={}
	selectedDst=False
	selected=[]
	totalLatency=0.0
	id=NSD["id"]
	name=NSD["name"]
	max_latency=NSD["max_latency"]

	parseVNFLINKS(NSD)
	parseSap(NSD)
	allocate(NSD,NFVIPOP,LLs) 
	#findNextHop(tempAlloc, single, coupled,LLs, NSD, NFVIPOP)
	if selectedDst:
		if totalLatency<=max_latency:
			return buildResponse(allocated, mapped,VirtualLinks)
		else:
			print "latency not respected"	
	else:
		print "no nfvipop available"


def allocate(NSD,NFVIPOP,LLs):
	global radius, longitude,latitude
	global cpu, ram, storage, allocated,mec
	global single, coupled
	first=False
	VNFs=NSD["VNFs"]
	for i in range(len(VNFs)):
		VNF=VNFs[i]["VNFid"]
		instances=VNFs[i]["instances"]
		requirements= VNFs[i]["requirements"]
		for key2 in requirements.keys():
			cpu=requirements["cpu"]
			ram=requirements["ram"]
			storage=requirements["storage"]
			if "mec" in requirements.keys():
				mec=requirements["mec"]
		if first==False:
			
			for j in range(len(VNFs[i]["CP"])):
				if VNFs[i]["CP"][j]["cpId"]==NSD["SAP"][0]['CPid']:
					
					checkSAPNodeAvailability(NFVIPOP,instances,cpu,ram,storage, mec,radius, longitude,latitude)	
					break	
				else: 
					checkNodeAvailability(NFVIPOP,instances,cpu,ram,storage)
			
			if NFVIPOPIdList:
					for i in range(len(NFVIPOPIdList)):
						selected=NFVIPOPIdList[i]
						tempAlloc[VNF]=selected
						first=True
						allocated[VNF]=selected[0]
						if findNextHop(tempAlloc, single, coupled,LLs, NSD, NFVIPOP):
							break
					
			else:
				print "No NFVIPOP available"
				return

	#findNextHop(tempAlloc, single, coupled,LLs, NSD, NFVIPOP)


def checkSAPNodeAvailability (NFVIPOP,numInstances,cpu,ram,storage, mec,radius, longitude, latitude):
	
	global nfviId, NFVIPOPIdList,totalLatency
	NFVIPOPIdList=[]
	for i in range(len(NFVIPOP)):
		nfvipop=NFVIPOP[i]
		if "mec" in NFVIPOP[i]["capabilities"].keys():
			#print NFVIPOP[i]
			if NFVIPOP[i]["capabilities"]["mec"]==True: #mumble
				pass
		else:
			NFVIPopLongitude=NFVIPOP[i]["location"]["center"]["longitude"]
			NFVIPopLatitude=NFVIPOP[i]["location"]["center"]["latitude"]
			if ((NFVIPopLatitude-latitude)**2+(NFVIPopLongitude-longitude)**2)<=radius**2:
				gwIP=nfvipop["gw_ip_address"]
				nfviId=nfvipop["id"]
				internal_latency=nfvipop["internal_latency"]
				availability(nfvipop)
				if not (cpu*numInstances<=AVcpu and ram*numInstances<=AVram and storage*numInstances<=AVstorage):
					return
				else:
					NFVIPOPIdList.append([nfviId,gwIP,internal_latency])
	NFVIPOPIdList=sorted(NFVIPOPIdList,key=itemgetter(2))
	#print NFVIPOPIdList
	return NFVIPOPIdList

def checkNextHopAvailability (NFVIPOP,dstid,instances,cpu,ram,storage,mec):
	global nfviId, NFVIPOPIdList
	for i in range(len(NFVIPOP)):
		nfvipop=NFVIPOP[i]
		if nfvipop['id']==dstid:
			if mec:
				if "mec" in nfvipop["capabilities"].keys():
					if nfvipop["capabilities"]["mec"]==True:
						availability(nfvipop)
						if not (cpu*instances<=AVcpu and ram*instances<=AVram and storage*instances<=AVstorage):
							return False		 
				else:
					return False
			else:
				availability(nfvipop)
				if not (cpu*instances<=AVcpu and ram*instances<=AVram and storage*instances<=AVstorage):
					return False
	return True

def checkNodeAvailability (NFVIPOP,numInstances,cpu,ram,storage):
	global nfviId, NFVIPOPIdList
	NFVIPOPIdList=[]
	for i in range(len(NFVIPOP)):
		nfvipop=NFVIPOP[i]
		gwIP=nfvipop["gw_ip_address"]
		nfviId=nfvipop["id"]
		internal_latency=nfvipop["internal_latency"]
		availability(nfvipop)
		if not (cpu*numInstances<=AVcpu and ram*numInstances<=AVram and storage*numInstances<=AVstorage):
			return
		else:
			NFVIPOPIdList.append([nfviId,gwIP,internal_latency])
	NFVIPOPIdList=sorted(NFVIPOPIdList,key=itemgetter(2))
	return NFVIPOPIdList

def parseSap(NSD):
	global radius, longitude,latitude
	SAP=NSD["SAP"]
	for kk in SAP[0].keys():
		if kk=="CPid":
			CPid=SAP[0][kk]
		if kk=="location":
			SAPLocation=SAP[0][kk]
			for kk2 in SAPLocation.keys():
				if kk2=="radius" and SAPLocation[kk2]==0:
					pass
				else:
					if kk2=="radius":
						radius= SAPLocation[kk2]
					if kk2=="center":
						longitude=SAPLocation[kk2]["longitude"]
						latitude =SAPLocation[kk2]["latitude"]
	return radius, latitude, longitude

def parseVNFLINKS(NSD):
	
	global single, coupled
	coupled={}
	single={}
	shared=[]
	for vl in NSD['VNFLinks']:
        # Search VNFs connected to vl
		connected_vnfs = []
		for vnf in NSD['VNFs']:
 			linked_cps = [cp for cp in vnf['CP']                      if 'VNFLink' in cp and cp['VNFLink']['id'] == vl['id']]
 			if linked_cps:
 				
	 			if not shared or shared[0]['VNFLink']['id']==linked_cps[0]['VNFLink']['id']:
		 			shared.append(linked_cps[0])
		 	
			if len(linked_cps) > 0:
				connected_vnfs.append(vnf['VNFid'])

		if len(connected_vnfs)==2:
			if (connected_vnfs[0],connected_vnfs[1]) not in coupled.keys():
				coupled[shared[0]['VNFLink']['id']]=[connected_vnfs[0],connected_vnfs[1]]
				#coupled[connected_vnfs[0],connected_vnfs[1]]=[shared[0]['VNFLink']['id']]
			else:
				coupled[shared[0]['VNFLink']['id']].append([connected_vnfs[0],connected_vnfs[1]])
			if connected_vnfs[0] not in single.keys():
				single[connected_vnfs[0]]=[[shared[0]['VNFLink']['id'],shared[0]['cpId'],connected_vnfs[1]]]
			else:
				single[connected_vnfs[0]].append ([shared[0]['VNFLink']['id'],shared[0]['cpId'],connected_vnfs[1]])
		shared=[]
	
	return single, coupled

def availability(nfvipop):
	global AVcpu, AVram, AVstorage

	AVcpu=nfvipop["availableCapabilities"]["cpu"]
	AVram=nfvipop["availableCapabilities"]["ram"]
	AVstorage=nfvipop["availableCapabilities"]["storage"]
	
	return AVstorage,AVram,AVcpu

def findNextHop(tempAlloc, single, coupled, LLs, NSD, NFVIPOP):
	
	global mapped, cpu, ram, storage,mec,totalLatency
	global allocated, selectedDst, totalLatency,VirtualLinks
	#totalLatency=0.0
	mapped=[]
	VirtualLinks=[]
	internal_latency=0.0
	mec=False

	for VNFid in single.keys():
		info=[]
		selLL=[]
		
		VNFsrcIPs=tempAlloc[tempAlloc.keys()[0]][1]#[0][1]
		for i in range(len(LLs)):
			LogicalLink=LLs[i]
			#for j in VNFsrcIPs:
			if LogicalLink["source"]["GwIpAddress"]==VNFsrcIPs:
				dest=LogicalLink['destination']['id']
				for dc in range(len(NFVIPOP)):
					if NFVIPOP[dc]['id']==dest:
						internal_latency=NFVIPOP[dc]['internal_latency']
						partialLatency=internal_latency+LogicalLink['delay']
						info.append([LogicalLink['LLid'],LogicalLink['delay'],LogicalLink['capacity']['available'],partialLatency])
		if len(info)>1:
			info=sorted(info,key=itemgetter(3))
		else:
			print "no LL available len info"
			return
		if VNFid==tempAlloc.keys()[0]:
			for vl in NSD['VNFLinks']:
				for m in range(len(single[VNFid])):
					vnfdst=single[VNFid][m][2]
					if vnfdst in allocated.keys(): #two connected VNF in the same POP
						if VNFid in tempAlloc.keys():
							if allocated[vnfdst]==tempAlloc[VNFid][0]:
								if [allocated[vnfdst],single[VNFid][m][0]] not in VirtualLinks:
									VirtualLinks.append([allocated[vnfdst],single[VNFid][m][0]])
					if vl['id']==single[VNFid][m][0]:
						required_capacity=vl['required_capacity']
						latency=vl['latency']
						if single[VNFid][m][2] in allocated.keys():

							selLL=[]
							dstDC=allocated[single[VNFid][m][2]]
							for i in range(len(LLs)):
								LogicalLink=LLs[i]
								for j in VNFsrcIPs:
									if LogicalLink["source"]["GwIpAddress"]==j:
										if LogicalLink["destination"]["id"]:
											selLL=[LogicalLink['LLid'],LogicalLink['delay'],LogicalLink['capacity']['available']]

						for l in range(len(info)):
							selLL=info[l]						
							if selLL[1]<=latency and selLL[2]>=required_capacity:
								
								for i in range(len(LLs)):
									LogicalLink=LLs[i]
									if LogicalLink['LLid']==selLL[0]:
										dstid=LogicalLink['destination']['id']
										if vl['id'] in coupled.keys():								
											if coupled[vl['id']][0]==VNFid:
												vnf=coupled[vl['id']][1]
												for aa in range(len(NSD['VNFs'])):
													if NSD['VNFs'][aa]['VNFid']==vnf:
			 										   	cpu=NSD['VNFs'][aa]['requirements']['cpu']
			 										   	ram=NSD['VNFs'][aa]['requirements']['ram']
			 										   	storage=NSD['VNFs'][aa]['requirements']['storage']
			 										   	if "mec" in NSD['VNFs'][aa]['requirements']:
				 										   	mec=NSD['VNFs'][aa]['requirements']['mec']
				 										else:
				 											mec=False
			 										   	instances=NSD['VNFs'][aa]['instances']
			 										   	if checkNextHopAvailability(NFVIPOP, dstid,instances,cpu,ram,storage,mec):
			 										   		allocated[vnf]=dstid
									   						if [selLL[0],vl['id']] not in mapped:
										   						mapped.append([selLL[0],vl['id']])

										   						totalLatency+=selLL[1]
									   						for p in range(len(NFVIPOP)):

								   								if NFVIPOP[p]['id']==dstid and vnf in single.keys():
								   									tempAlloc={}
											   						tempAlloc[vnf]=[dstid,NFVIPOP[p]['gw_ip_address'],NFVIPOP[p]['internal_latency']]
											   						
											   						break
							else:
								print "reject"
								return
							if [selLL[0],vl['id']] in mapped:
								break
					if len(allocated.keys())==len(NSD["VNFs"]):
						break
	for v in allocated.keys():
		for x in range(len(NFVIPOP)):
			if allocated[v]==NFVIPOP[x]['id']:

				totalLatency+=NFVIPOP[x]['internal_latency']
	if len(allocated.keys())==len(NSD["VNFs"]) and len(mapped)+len(VirtualLinks)==len(NSD['VNFLinks']):
		#computeTotalLatency(mapped,allocated,NFVIPOP,LLs)
		selectedDst=True							   					
	#print totalLatency
	#mapped=list(set(mapped))
	#print mapped,allocated, VirtualLinks
	return mapped, allocated, totalLatency, selectedDst, VirtualLinks

def computeTotalLatency(mapped,allocated,NFVIPOP,LLs):
	totalLatency=0.0
	for i in range(len(mapped)):
		print mapped[i]
	for  j in allocated.keys():
		print j

def buildResponse(allocated, mapped,VirtualLinks):
	#global totalLatency
	
	response={"usedNFVIPops":[],"usedLL":[],"usedVL":[],"totalLatency":totalLatency}
	for k in allocated.keys():
		pop={"NFVIPopID":allocated[k][0],"mappedVNFs":k}
		response["usedNFVIPops"].append(pop)
	for i in range(len(mapped)):
		lls={"LLID":mapped[i][0],"mappedVLs":mapped[i][1]}
		response["usedLL"].append(lls)
	for l in range(len(VirtualLinks)):
		vls={"NFVIPoP":VirtualLinks[l][0],"mappedVLs":VirtualLinks[l][1]}
		response["usedVL"].append(vls)

	#print response
	return response