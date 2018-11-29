Id=""
name=""
cpuS=0
ramS=0
storageS=0
cpuD=0
ramD=0
storageD=0
max_latency=0
src=""
required_capacity=0
instancesSRC=0
instancesDST=0
VNFSRC=""
VNFDST=""
AVcpu=0
AVram=0
AVstorage=0
selectedDst=[]
selectedDC=""
closest=0
nfviId=""
nfviSrcId=""
totalLatency=0.0

def PAdist(NFVIPOP,LLs,NSD):
	global selectedDst, selectedDC, instancesSRC, instancesDST,nfviId, nfviSrcId
	parseRequest(NSD) #pensa se necessaria
	if checkNodeAvailability(NFVIPOP,src,instancesSRC,cpuS,ramS,storageS):
		#print nfviId
		nfviSrcId=nfviId
		look4Dst(LLs,NFVIPOP,instancesDST)
		if selectedDst:
			return buildResponse()
			#print selectedDst
		else:
			print "no dst"
	else:
		print "no src"
	#look4Dst()
	
	
	#return solution


def parseRequest(NSD):
	global src, cpuS,ramS, storageS, cpuD,ramD, storageD, instancesDST,instancesSRC,required_capacity, VNFSRC,VNFDST
	VNFs={}
	VNFLinks={}
	requirements=[]
	for key in NSD.keys():
		if key=="Id":
			Id=NSD[key]
		if key=="name":
			name=NSD[key]
		if key=="max_latency":
			max_latency=NSD[key]
		if key=="VNFs":
			VNFs=NSD[key]
			if len(VNFs)==2:
				srcInfo=VNFs[0]
				dstInfo=VNFs[1]
				for key1 in srcInfo.keys():
					if key1=="VNFid":
						VNFSRC=srcInfo[key1]
					if key1=="instances":
						instancesSRC=srcInfo[key1]
					if key1=="requirements":
						requirements= srcInfo[key1]
						for key2 in requirements.keys():
							if key2=="cpu":
								cpuS=requirements[key2]
							if key2=="ram":
								ramS=requirements[key2]
							if key2=="storage":
								storageS=requirements[key2]	
				
				for key3 in dstInfo.keys():
					if key3=="VNFid":
						VNFDST=dstInfo[key3]
					if key3=="instances":
						instancesDST=dstInfo[key3]
					if key3=="requirements":
						requirements= dstInfo[key3]
						for key2 in requirements.keys():
							if key2=="cpu":
								cpuD=requirements[key2]
							if key2=="ram":
								ramD=requirements[key2]
							if key2=="storage":
								storageD=requirements[key2]
				
			#else:
				#TBD
		if key=="VNFLinks":
			VNFLinks=NSD[key][0]
			for key1 in VNFLinks.keys():
				if key1=="source":
					src=VNFLinks[key1]
				if key1=="required_capacity":
					required_capacity=VNFLinks[key1]
	return src,instancesSRC,instancesDST,cpuS,ramS,storageS, cpuD,ramD,storageD,required_capacity,max_latency

def checkNodeAvailability (NFVIPOP,gw_ip_address,numInstances,cpu,ram,storage):
	global nfviId
	for i in range(len(NFVIPOP)):
		nfvipop=NFVIPOP[i]
		for k in nfvipop.keys():
			if nfvipop[k]==gw_ip_address:
				#print nfvipop
				for k1 in nfvipop.keys():
					if k1=="Id":
						nfviId=nfvipop[k1]
						availability(nfvipop)
	if not (cpu*numInstances<=AVcpu and ram*numInstances<=AVram and storage*numInstances<=AVstorage):
		return
	else:
		return True	

def  look4Dst(LLs,NFVIPOP,instancesDST):
	global src, selectedDst, selectedDC,required_capacity, totalLatency
	possibleDst=''
	LLid=''
	distanceDict={}
	j=0
	idDst=''
	lengthList=[]
	for i in range(len(LLs)):
		LogicalLink=LLs[i]
		for k in sorted(LogicalLink.keys()):
			if k=="LLid":
				LLid=LogicalLink[k]
			if k=="source":
				srcData=LogicalLink[k]
				for k1 in srcData:
					if k1=="GwIpAddress":
						if srcData[k1]==src:
							for k2  in LogicalLink.keys():
								if k2=="destination":
									dstData=LogicalLink[k2]
									for k3 in dstData.keys():
										if k3=="Id":
											idDst=dstData[k3]
										if k3=="GwIpAddress":
											possibleDst=dstData[k3]
											if checkNodeAvailability(NFVIPOP,possibleDst,instancesDST,cpuD,ramD,storageD):
												for k4 in LogicalLink.keys():
													if k4=="capacity":
														capacity=LogicalLink[k4]
														for el in capacity.keys():
															if el=="available":
																availableBw=capacity[el]
																if availableBw>=required_capacity:
																	for k5 in LogicalLink.keys():
																		if k5=="delay":
																			delay=LogicalLink[k5]
																		if k5=="length":
																			length=LogicalLink[k5]
																			distanceDict[idDst]=[possibleDst, length,delay, LLid]
																else:
																	print "not enough banwidth"
																	return False
											else:
												print "no available dst"
												return
												
														
	if distanceDict:
		distancelist=distanceDict.values()
		for i in range(len(distancelist)):
			lengthList.append(distancelist[i][1])
			
	if lengthList:
		closest=min(lengthList)
		j=lengthList.index(closest)
		selectedDC=distanceDict.keys()[j]
		selectedDst=distanceDict[selectedDC]
		totalLatency=selectedDst[2]
				
		
	return selectedDst,selectedDC
	
def buildResponse():
	global cpuD,ramD,storageD,instancesDST
	#response={"NFVIPOP":[{"id":selectedDC,"CPU":cpuD*instancesDST,"RAM":ramD*instancesDST,"Storage":storageD*instancesDST}],"LL":[{"LLid":selectedDst[2], "gwIPSrc":src,"gwIPDst":selectedDst[0]}],"TotalLength":selectedDst[1]}
	response={"NFVIPOP":[{"NFVIPopID":nfviSrcId,"mappedVNFs":[VNFSRC]},{"NFVIPopID":selectedDC,"mappedVNFs":[VNFDST]}],"usedLL":[{"LLid":selectedDst[2]}],"totalLatency":totalLatency}
	return response

def availability(nfvipop):
	global AVcpu, AVram, AVstorage
	for j in nfvipop.keys():
		if j=="availableCapabilities":
			availableCapabilities=nfvipop[j]
			for k1 in availableCapabilities.keys():
				if k1=="cpu":
					AVcpu=availableCapabilities[k1]
				if k1=="ram":
					AVram=availableCapabilities[k1]
				if k1=="storage":
					AVstorage=availableCapabilities[k1]				
	return AVstorage,AVram,AVcpu
