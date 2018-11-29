

from marshmallow import Schema, fields

class PAreq(object):
	def __init__(self,ReqId,NFVI,NSD,callback):
		self.ReqId=ReqId
		self.nfvi=nfvi
		self.nsd=nsd
		self.callback=callback

		def __repr__(self):
			return '<PAreq(ReqId={self.ReqId!r})>'.format(self=self)

class nfvi(object):
	def __init__(self,resource_Types, NFVIPoPs, LLs, VNFCOst,LLcost,VLCost):
		self.resource_Types=resource_Types
		self.NFVIPoPs=NFVIPoPs
		self.LLs=LLs
		self.VNFCOst=VNFCOst
		self.LLcost=LLcost
		self.VLCost=VLCost
	def __repr__(self):
			return '<nfvi(resource_Types={self.resource_Types!r})>'.format(self=self)		

class NFVIPoP(object):
	def __init__(self,Id,location,gw_ip_address,capabilities,availableCapabilities,failureRate,internal_latency):
		self.Id=Id
		self.location=location
		self.gw_ip_address=gw_ip_address
		self.capabilities=capabilities
		self.availableCapabilities=availableCapabilities
		self.failureRate=failureRate
		self.internal_latency=internal_latency
	def __repr__(self):
			return '<NFVIPoP(Id={self.Id!r})>'.format(self=self)		

class location(object):
	def __init__(self, center, radius):
		self.center=center
		self.radius=radius

class center(object):
	def  __init__(self,latitude,longitude):
		self.latitude=latitude
		self.longitude=longitude

class capabilities:
	def __init__(self,cpu,ram,storage, bw):
		self.cpu=cpu
		self.ram=ram
		self.storage=storage
		self.bw=bw

class availableCapabilities:
	def __init__(self,cpu,ram,storage, bw):
		self.cpu=cpu
		self.ram=ram
		self.storage=storage
		self.bw=bw


class LL(object):
	def __init__(self,LLid,capacity,delay,length,source,destination):
		self.LLid=LLid
		self.capacity=capacity
		self.delay=delay
		self.length=length
		self.source=source
		self.destination=destination
	def __repr__(self):
			return '<LL(LLid={self.LLid!r})>'.format(self=self)

class capacity(object):
	def __init__(self,total,available):
		self.total=total
		self.available=available

class source(object):
	def __init__(self,Id,GwIpAddress):
		self.Id=Id
		self.GwIpAddress=GwIpAddress


class dstination(object):
	def __init__(self,Id,GwIpAddress):
		self.Id=Id
		self.GwIpAddress=GwIpAddress
class VNFCost(object):
	def __init__(self,cost,VNFid,NFVIPoPId):
		self.cost=cost
		self.VNFid=VNFid
		self.NFVIPoPId=NFVIPoPId

class LLcost(object):
	"""docstring for LLCos"""
	def __init__(self,cost,LLid):
		self.cost = cost
		selfLLid=LLid

class VLCost(object):
	"""docstring for VLCost"""
	def __init__(self, cost,NFVIPoPId):
		self.cost = cost
		self.NFVIPoPId=NFVIPoPId
		
		


class nsd(object):
	def __init__(self,Id,name,VNFs,VNFLinks,max_latency,targetAvail,maxCost):
		self.Id=Id
		self.name=name
		self.VNFs=VNFs
		self.VNFLinks=VNFLinks
		self.max_latency=max_latency
		self.targetAvail=targetAvail
		self.maxCost=maxCost
	def __repr__(self):
			return '<nsd(Id={self.Id!r})>'.format(self=self)


class VNFs(object):
	def __init__(self, VNFid,instances,location,requirements,failureRate,processingLatency):
	
		self.VNFid=VNFid
		self.instances=instances
		#self.instancesDST=instancesDST
		self.location=location
		self.requirements=requirements
		self.failureRate=failureRate
		self.processingLatency=processingLatency

class requirements(object):
	def __init__(self,cpu, ram, storage):
		self.cpu=cpu
		self.ram=ram
		self.storage=storage
		

class VNFLinks(object):
	def __init__(self,source,destination,required_capacity,traversal_prob):
		self.source=source
		self.destination=destination
		self.required_capacity=required_capacity
		self.traversal_prob=traversal_prob

class centerSchema(Schema):
	latitude=fields.Float(required=True)
	longitude=fields.Float(required=True)


class locationSchema(Schema):
	center=fields.Nested(centerSchema)
	radius=fields.Float(required=True)


class capabilitiesSchema(Schema):
	cpu=fields.Float(required=True)
	ram=fields.Float(required=True)
	storage=fields.Float(required=True)
	bw=fields.Float()

class availableCapabilitiesSchema(Schema):
	cpu=fields.Float(required=True)
	ram=fields.Float(required=True)
	storage=fields.Float(required=True)
	bw=fields.Float()

class NFVIPoPsSchema(Schema):
	Id=fields.String(required=True)
	location=fields.Nested(locationSchema)
	gw_ip_address=fields.String()
	capabilities=fields.Nested(capabilitiesSchema, required=True)
	availableCapabilities=fields.Nested(availableCapabilitiesSchema)
	failureRate=fields.Float()
	internal_latency=fields.Float()

class capacitySchema(Schema):
	total=fields.Float(required=True)
	available=fields.Float(required=True)

class sourceSchema(Schema):
	Id=fields.String(required=True)
	GwIpAddress=fields.String(required=True)


class dstSchema(Schema):
	Id=fields.String(required=True)
	GwIpAddress=fields.String(required=True)


class LLsSchema(Schema):
	LLid=fields.String(required=True)
	capacity=fields.Nested(capacitySchema, required=True)
	delay=fields.Float(required=True)
	length=fields.Float()
	source=fields.Nested(sourceSchema, required=True)
	destination=fields.Nested(dstSchema, required=True)

class VNFCostSchema(Schema):
	cost=fields.Float(required=True)
	VNFid=fields.String(required=True)
	NFVIPoPId=fields.String(required=True)

class LLcostSchema(Schema):
	cost=fields.Float(required=True)
	LLid=fields.String(required=True)

class VLCostSchema(Schema):
	cost=fields.Float(required=True)
	NFVIPoPId=fields.String(required=True)
		


class NFVISchema(Schema):
	resource_Types=fields.String()
	NFVIPoPs=fields.Nested(NFVIPoPsSchema, required=True, many=True)
	LLs=fields.Nested(LLsSchema, required=True, many=True)
	VNFCOst=fields.Nested(VNFCostSchema,many=True)
	LLcost=fields.Nested(LLcostSchema,many=True)
	VLCost=fields.Nested(VLCostSchema,many=True)

class requirementsSchema(Schema):
	cpu=fields.Float()
	ram=fields.Float()
	storage=fields.Float()



class VNFsSchema(Schema):
	VNFid=fields.String(required=True)
	instances=fields.Int(required=True)
	#instancesDST=fields.Int(required=True)
	location=fields.Nested(locationSchema)
	requirements=fields.Nested(requirementsSchema, required=True)
	failureRate=fields.Float()
	processingLatency=fields.Float()



class VNFLinksSchema(Schema):
	source=fields.String(required=True)
	destination=fields.String()
	required_capacity=fields.Float()
	traversal_prob=fields.Float()

class NSDSchema(Schema):
	Id=fields.String(required=True)
	name=fields.String(required=True)
	VNFs=fields.Nested(VNFsSchema, many=True, required=True)
	VNFLinks=fields.Nested(VNFLinksSchema, many=True,required=True)
	max_latency=fields.Float()
	targetAvail=fields.Float()
	maxCost=fields.Float()
		

class PAreqSchema(Schema):
	ReqId=fields.String(required=True)
	nfvi=fields.Nested(NFVISchema, required=True)
	nsd=fields.Nested(NSDSchema, required=True)
	callback=fields.String(required=True)







	

