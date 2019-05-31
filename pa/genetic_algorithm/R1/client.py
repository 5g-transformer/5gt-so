# -*- coding: utf-8 -*-

"""
Copyright 2018 Pantelis Frangoudis, EURECOM

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
#################################################################
A client program for testing placement algorithms.

To run it:
python client.py -c /path/to/algorithm/input/file.json
#################################################################
"""

import httplib
import sys
import getopt
import json
import threading
import time
import uuid
from flask import Flask, jsonify, request
from flask_restful import reqparse, abort, Api, Resource

# Placement algorithm API enedpoint
host = "127.0.0.1"
port = 6161
apiurl = "/5gt/so/v1/PAComp"

# File to output solution
out_path = None

def execute(request_content):
  """Request the execution of the placement algorithm.

  This function accesses the placement algorithm API endpoint and requests the calculation
  of a placement for the given input (PACompReq). The latter should point to a valid path. 
  This call generates and puts in the request a unique request ID and receives/outputs the
  result of the execution of the algorithm.
  """

  global out_path
  
  jcontent = {}
  # check if request body is well formatted
  try:
      req = json.dumps(json.loads(request_content))
  except:
      print "Malformed data"
      sys.exit(1)

  # create the body of the request
  jcontent.update(json.loads(req))
  # if reqid and callback are already there, overwrite them
  jcontent["ReqId"] = str(uuid.uuid4())
  
  headers = {"Content-Type":"application/json"}

  print "Calling placement algorithm API"
  print "[POST]\t" + apiurl
  print "-----------------------"

  # send request
  cnx = httplib.HTTPConnection(host, port)
  cnx.request(method="POST", url=apiurl, body=json.dumps(jcontent), headers=headers)
  r = cnx.getresponse()
  if r.status == 200 or r.status == 201:
    resp_body = json.loads(r.read())
  
    # check whether to output solution in a file or to stdout
    tostdout = False
    if out_path is not None:
      try:
        outf = open(out_path, "w")
      except:
        print "Could not open solution output file. Using stdout instead."
        tostdout = True
    else:
      tostdout = True
    
    if tostdout:
      print json.dumps(resp_body, indent=2)
    else:
      json.dump(resp_body, outf, indent=2)

    print "#############################################"
    print "Total cost: " + str(resp_body["totalCost"])
    print "Total latency:" + str(resp_body["totalLatency"])
  else:
    print r.status, r.reason

if __name__ == '__main__':
  req = None
  # get input from cmd line
  myopts, args = getopt.getopt(sys.argv[1:], "i:o:")
  for o, a in myopts:
    if o == "-i":
      req = a
    elif o == "-o":
      out_path = a

  # Output file is optional. If not specified, dump everything to stdout
  if not req:
    print "Missing input. Usage: python client.py -i /path/to/request/info.json [-o /path/to/output/file.json]"
    sys.exit(1)

  # load algorithm input
  try:
    f = file(req)
    request_content = f.read()
  except:
    print "Error reading " + req
    sys.exit(1)

  # execute request
  execute(request_content)

