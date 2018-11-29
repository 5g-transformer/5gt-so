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
A client program for testing placement algorithms. This operates 
as follows:
- Sends a request to the placement algorithm's API endpoint including
in the request the ReqId, callback URL and algorithm input
- Starts an HTTP server to receive the algorithm output asynchronously
on a specified callback URL.
- Terminates after it has received the placement algorithm's outcome.  

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

# Callback URL information
callback_port = 9999
callback_uri = "/5gt/so/v1/PACompResp"
callback_host = "http://127.0.0.1"

# Flag to set when done so that the program exits
stopped = False

# File to output solution
out_path = None

def execute(request_content, callback):
  """Request the execution of the placement algorithm.

  This function accesses the placement algorithm API endpoint and requests the calculation
  of a placement for the given input (PACompReq). The latter should point to a valid path. 
  This call generates and puts in the request a unique request ID and registers a callback URL which will be used
  by the placement algorithm front end to notify the caller about the outcome of the algorithm.
  """

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
  jcontent["callback"] = callback
  
  headers = {"Content-Type":"application/json"}

  print "Calling placement algorithm API"
  print "[POST]\t" + apiurl
  print "-----------------------"

  # send request
  cnx = httplib.HTTPConnection(host, port)
  cnx.request(method="POST", url=apiurl, body=json.dumps(jcontent), headers=headers)
  r = cnx.getresponse()
  print r.status, r.reason
  print r.read()


def receive_response():
  """Callback handler.

  This function will be called when the placement algorithm front end
  accesses the callback API endpoint to report the outcome of the placement algorithm.
  The local API server is stop and the program is signalled to exit.
  """
  global stopped
  global out_path

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
    print json.dumps(request.json, indent=2)
  else:
    json.dump(request.json, outf, indent=2)

  print "#############################################"
  print "Total cost: " + str(request.json["totalCost"])
  print "Total latency:" + str(request.json["totalLatency"])

  # set exit flag
  stopped = True
  return jsonify({"result": "Success"}), 200


def start_server():
  """This function registers the API handler and starts the server at the specified port.
  """
  app = Flask(__name__)
  app.add_url_rule(callback_uri, 'receive_response', receive_response, methods=['POST'])
  app.run(host="0.0.0.0", port=callback_port)


if __name__ == '__main__':
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

  # spawn thread to await PA response
  t = threading.Thread(target=start_server)
  t.setDaemon(True)
  t.start()

  # execute request
  callback = callback_host + ":" + str(callback_port) + callback_uri
  execute(request_content, callback)

  # Loop until signalled to stop (Ctrl-C or simply upon reception of the algorithm output)
  try:
    while not stopped:
      pass
  except KeyboardInterrupt:
    print("exiting")
    sys.exit(0)

  # just sleep for a while to be sure the HTTP response has been completed
  time.sleep(1)

