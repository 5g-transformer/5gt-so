import random
from operator import itemgetter
from itertools import combinations
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
selLL=[]
vlid=''
VirtualLinks=[]
selectedDst=False
totalLatency=0.0
mec=False
cpx=''
VNFLinkSap=''

# -totalcost va nella risp anche se non lo considero?

def PAdist(NFVIPOP,LLs,NSD):
	global nfviId, totalLatency, selected, selectedDst, allocated,totalLatency, mapped, VirtualLinks
	allocated={}
	mapped=[]
	VirtualLinks=[]
	totalLatency=0.0
	selectedDst=False
	selected=[]
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
	global radius, longitude,latitude, VNFLinkSap
	global cpu, ram, storage, allocated,mec
	global single, coupled, VirtualLinks
	first=False
	VNFs=NSD["VNFs"]
	for v in single.keys():
		for i in range(len(VNFs)):
			if v==VNFs[i]["VNFid"]:
				VNF=VNFs[i]["VNFid"]
				instances=VNFs[i]["instances"]
				requirements= VNFs[i]["requirements"]
				for key2 in requirements.keys():
					cpu=requirements["cpu"]
					ram=requirements["ram"]
					storage=requirements["storage"]
					if "mec" in requirements.keys():
						mec=requirements["mec"]
				#if first==False:
				if VNF not in allocated.keys():
					
					for j in range(len(VNFs[i]["CP"])):
						for p in range(len(NSD["SAP"])):
							if VNFs[i]["CP"][j]["VNFLink"]['id']==VNFLinkSap:
								checkSAPNodeAvailability(NFVIPOP,instances,cpu,ram,storage, mec,radius, longitude,latitude)	
								break	
							else: 
								checkNodeAvailability(NFVIPOP,instances,cpu,ram,storage)
					
					if NFVIPOPIdList:

						tempAlloc={}

						for j in range(len (single[VNF])):
							latency=0.0
							relatedLL=single[VNF][j][0]
							for vl in NSD['VNFLinks']:
								if vl['id'] in coupled.keys() and vl['id']==relatedLL :
							#		required_capacity=vl['required_capacity']
									latency=vl['latency']
									src=vl['source']
									dst=vl['destination']

							if single[VNF][j][2] in allocated.keys() and latency==0:

								for i in range(len(NFVIPOPIdList)):
									if NFVIPOPIdList[i][0]==allocated[single[VNF][j][2]]:
										selected= NFVIPOPIdList[i]
										if [selected[0],relatedLL,src,dst] not in VirtualLinks:
											VirtualLinks.append([selected[0],relatedLL,src,dst])
											
							else:
								selected=random.choice(NFVIPOPIdList) #in ML questo non e' random, va considerata la latenza interna del Dc
						tempAlloc[VNF]=selected
						first=True
						allocated[VNF]=selected[0]
						if findNextHop(tempAlloc, single, coupled,LLs, NSD, NFVIPOP):
								break
							
					else:
						print "No NFVIPOP available"
						return
				else:
					for g in range(len(single[VNF])):
						vnfdst= single[VNF][g][2]
						vl=single[VNF][g][0]
						if vnfdst in allocated.keys():
							if allocated[VNF]==allocated[vnfdst]:
								if [allocated[VNF],vl,VNF,vnfdst] not in VirtualLinks:
									if [allocated[VNF],vl,vnfdst,VNF] not in VirtualLinks:
										VirtualLinks.append([allocated[VNF],vl,VNF,vnfdst])
							

def checkSAPNodeAvailability (NFVIPOP,numInstances,cpu,ram,storage, mec,radius, longitude, latitude):
	
	global nfviId, NFVIPOPIdList
	NFVIPOPIdList=[]
	for i in range(len(NFVIPOP)):
		nfvipop=NFVIPOP[i]
		if "mec" in NFVIPOP[i]["capabilities"].keys():
			if NFVIPOP[i]["capabilities"]["mec"]==True: #mumble
				NFVIPopLongitude=NFVIPOP[i]["location"]["center"]["longitude"]
				NFVIPopLatitude=NFVIPOP[i]["location"]["center"]["latitude"]
				a=(NFVIPopLatitude-latitude)**2
				
				if ((NFVIPopLatitude-latitude)**2+(NFVIPopLongitude-longitude)**2)<=radius**2:
					
					gwIP=nfvipop["gw_ip_address"]
					nfviId=nfvipop["id"]
					availability(nfvipop)
					if not (cpu*numInstances<=AVcpu and ram*numInstances<=AVram and storage*numInstances<=AVstorage):
						return
					else:
						NFVIPOPIdList.append([nfviId,gwIP])
		else:
			
			NFVIPopLongitude=NFVIPOP[i]["location"]["center"]["longitude"]
			NFVIPopLatitude=NFVIPOP[i]["location"]["center"]["latitude"]
			if ((NFVIPopLatitude-latitude)**2+(NFVIPopLongitude-longitude)**2)<=radius**2:
				gwIP=nfvipop["gw_ip_address"]
				nfviId=nfvipop["id"]
				availability(nfvipop)
				if not (cpu*numInstances<=AVcpu and ram*numInstances<=AVram and storage*numInstances<=AVstorage):
					return
				else:
					NFVIPOPIdList.append([nfviId,gwIP])
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
		availability(nfvipop)
		if not (cpu*numInstances<=AVcpu and ram*numInstances<=AVram and storage*numInstances<=AVstorage):
			return
		else:
			NFVIPOPIdList.append([nfviId,gwIP])
	#print NFVIPOPIdList
	return NFVIPOPIdList

def parseSap(NSD):
	global radius, longitude,latitude, VNFLinkSap
	SAP=NSD["SAP"]
	for kk in range(len(SAP)):
		if "location" in SAP[kk].keys():
			VNFLinkSap=SAP[kk]["VNFLink"]
			radius=SAP[kk]["location"]['radius']
			longitude=SAP[kk]["location"]['center']['longitude']
			latitude=SAP[kk]["location"]['center']['latitude']

	return VNFLinkSap,radius, latitude, longitude

def parseVNFLINKS(NSD):
	
	global single, cpx
	single={}
	shared=[]
	generateCoupled(NSD)
	if coupled:
 		for vnf in NSD['VNFs']:
	 		for t in vnf['CP']:
		 		for c in coupled.keys():
		 			cpx=''
		 			for v in range(len(coupled[c])):
		 				if coupled[c][v][0]==vnf['VNFid']:
		 					if t['VNFLink']['id']==c:
		 						cpx=t['cpId']
		 						if not single.keys() or coupled[c][v][0] not in single.keys():
		 							single[coupled[c][v][0]]=[[c,cpx,coupled[c][v][1]]]
		 						elif [c,cpx,coupled[c][v][1]] not in single[coupled[c][v][0]]:
			 						single[coupled[c][v][0]].append([c,cpx,coupled[c][v][1]])
	#print single
	return single

def generateCoupled(NSD):
	global coupled
	coupled={}
	for vl in NSD['VNFLinks']:
		connected_vnfs = []
		for vnf in NSD['VNFs']:
 			linked_cps = [cp for cp in vnf['CP']                      if 'VNFLink' in cp and cp['VNFLink']['id'] == vl['id']]
			if len(linked_cps) > 0:
				connected_vnfs.append(vnf['VNFid'])
			for VNFe in list(combinations(connected_vnfs, 2)):
				if not coupled.keys() or vl['id'] not in coupled.keys():
					coupled[vl['id']]=[[VNFe[0],VNFe[1]]]
				elif [VNFe[0],VNFe[1]] not in coupled[vl['id']] :
					coupled[vl['id']].append([VNFe[0],VNFe[1]])
	#print coupled
	return coupled

def availability(nfvipop):
	global AVcpu, AVram, AVstorage
	AVcpu=nfvipop["availableCapabilities"]["cpu"]
	AVram=nfvipop["availableCapabilities"]["ram"]
	AVstorage=nfvipop["availableCapabilities"]["storage"]
	return AVstorage,AVram,AVcpu

def findNextHop(tempAlloc, single, coupled, LLs, NSD, NFVIPOP):
	
	global mapped, cpu, ram, storage,mec,totalLatency, selLL, vlid
	global allocated, selectedDst, totalLatency,VirtualLinks, VNFLinkSap
	
	mec=False
	for VNFid in single.keys():
		info=[]
		selLL=[]
		vlid=''
		VNFsrcIPs=tempAlloc[tempAlloc.keys()[0]][1]
		parseLogicalLinks(LLs,NFVIPOP,VNFsrcIPs,info)

		if VNFid==tempAlloc.keys()[0]:
			#for vl in NSD['VNFLinks']:
			for m in range(len(single[VNFid])):
				vnfdst=single[VNFid][m][2]
				relatedLL=single[VNFid][m][0]
				if vnfdst in allocated.keys():
					dstDC=allocated[vnfdst]
					if VNFid in tempAlloc.keys():
						if dstDC==tempAlloc[VNFid][0]:
							if ([dstDC,relatedLL,VNFid,vnfdst]) not in VirtualLinks:
								if  [dstDC,relatedLL,vnfdst, VNFid] not in VirtualLinks:
									VirtualLinks.append([dstDC,relatedLL,VNFid,vnfdst]) #map to a VLINK
						else: #VNFs already allocated in 2 different POP
							VLmapping(NSD,relatedLL,info)
							if selLL:
								if [selLL[0],vlid] not in mapped:
			   						mapped.append([selLL[0],vlid])
			   						totalLatency+=selLL[1]
			   					
			   				else:
			   					print "not selLL"

		   		else:
		   			#print "not allocated"
		   			VLmapping(NSD,relatedLL,info)
		   			if not selLL:
		   				if vlid in coupled.keys():
		   					for e in range(len(coupled[vlid])):
								if coupled[vlid][e][0]==VNFid:
									vnf=coupled[vlid][e][1]
									if vnf not in allocated.keys():
										if VNFid in tempAlloc.keys():
											dstid=tempAlloc[VNFid][0]
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
											   				if [dstid,vlid,VNFid,vnf] not in VirtualLinks:
											   					VirtualLinks.append([dstid,vlid, VNFid,vnf])
														#REMOVED TO ALLOCATE ALL ll. cHECK WITH OTHER SCENARION
														#for p in range(len(NFVIPOP)):
							   							#	if NFVIPOP[p]['id']==dstid and vnf in single.keys():
							   							#		tempAlloc={}
										   				#		tempAlloc[vnf]=[dstid,NFVIPOP[p]['gw_ip_address']]
										else:
											allocated[vnf]=allocated[VNFid]
											#print allocated	   
		   				#alloca la vnf nello stesso pop (se c'e' spazio) e assoia il VNFLInk a un VL
		   			
		   			else:
			   			for i in range(len(LLs)):
							LogicalLink=LLs[i]
							if LogicalLink['LLid']==selLL[0]:
								
								dstid=LogicalLink['destination']['id']
								if vlid in coupled.keys():
									for e in range(len(coupled[vlid])):
										if coupled[vlid][e][0]==VNFid:
											vnf=coupled[vlid][e][1]
											if vnf not in allocated.keys():
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
			 										   	CPs=NSD['VNFs'][aa]['CP']
				 										for r in range(len(CPs)):
				 											
					 										if CPs[r]['vl_id']==VNFLinkSap:
				 										   		checkSAPNodeAvailability(NFVIPOP,instances,cpu,ram,storage, mec,radius, longitude,latitude)
			 										   		else:
			 										   			checkNextHopAvailability(NFVIPOP, dstid,instances,cpu,ram,storage,mec)
			 										   		allocated[vnf]=dstid
									   						if [selLL[0],vlid] not in mapped:
										   						mapped.append([selLL[0],vlid])
																totalLatency+=selLL[1]
									   						for p in range(len(NFVIPOP)):
								   								if NFVIPOP[p]['id']==dstid and vnf in single.keys():
								   									tempAlloc={}
											   						tempAlloc[vnf]=[dstid,NFVIPOP[p]['gw_ip_address']]
										   						
				# 		else:
				# 			print "reject"
				# 			return
				# 		if [selLL[0],vl['id']] in mapped:
				# 			break
				# if len(allocated.keys())==len(NSD["VNFs"]):
				# 	break
	for v in allocated.keys():
		for x in range(len(NFVIPOP)):
			if allocated[v]==NFVIPOP[x]['id']:
				#print NFVIPOP[x]['id'],NFVIPOP[x]['internal_latency']
				totalLatency+=NFVIPOP[x]['internal_latency']
	if len(allocated.keys())==len(NSD["VNFs"]):# and len(mapped)+len(VirtualLinks)==len(NSD['VNFLinks']):
		selectedDst=True							   					
	#print totalLatency
	#mapped=list(set(mapped))
	return mapped, allocated, totalLatency, selectedDst, VirtualLinks

def parseLogicalLinks(LLs,NFVIPOP, VNFsrcIPs,info):
	#from the "source" VNF computes all the LLs connected to it and returns an ordered array with the the LLs characteristics 
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
	
	if len(info)>=1:
		info=sorted(info,key=itemgetter(3))
	else:
		print "no LL available len info"
		return
	return info

def VLmapping(NSD, relatedLL,info):
	global selLL, vlid, VNFLinkSap, coupled
	latency=0.0
	required_capacity=0.0
	
	for vl in NSD['VNFLinks']:
		if vl['id']==relatedLL and vl['id'] in coupled.keys():
			required_capacity=vl['required_capacity']
			latency=vl['latency']
			for l in range(len(info)):
				selLL=info[l]
				if latency==0:
					vlid=vl['id']
					selLL=[]
					return vlid					
				elif selLL[1]<=latency and selLL[2]>=required_capacity:
					vlid=vl['id']
					return selLL,vlid
				else:
					vlid=vl['id']
					selLL=[]
					return vlid		

def buildResponse(allocated, mapped,VirtualLinks):
	#global totalLatency
	response={"usedNFVIPops":[],"usedLLs":[],"usedVLs":[],"totalLatency":totalLatency}
	allocated2 = {} 
	for key, value in allocated.items(): 
   		if value in allocated2:
   			allocated2[value].append(key) 
		else:
			allocated2[value]=[key] 
	for k in allocated2.keys():
		pop={"NFVIPoPID":k,"mappedVNFs":allocated2[k]}
		response["usedNFVIPops"].append(pop)
	mapped2={}
	for m in mapped:
		if  m[0] in mapped2.keys():
			mapped2[m[0]].append(m[1])
		else:
			mapped2[m[0]]=[m[1]]
	for i in mapped2.keys():
		lls={"LLID":i,"mappedVLs":mapped2[i]}
		response["usedLLs"].append(lls)
	VirtualLinks2={}
	for m in VirtualLinks:
		if  m[0] in VirtualLinks2.keys():
			VirtualLinks2[m[0]].append(m[1])
		else:
			VirtualLinks2[m[0]]=[m[1]]

	for l in VirtualLinks2.keys():
		vls={"NFVIPoP":l,"mappedVLs":VirtualLinks2[l]}
		response["usedVLs"].append(vls)
	return response