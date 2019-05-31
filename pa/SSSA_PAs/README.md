In this folder there are two folders with the two different algorithms. The first one minimize the distance (network delay) between the NFVIPoP, the second one minimize the overall latency, by considering also the internal processing latency of each NFVIPoP.
In both folders there are:
- server.py
- PASchema.py (to validate the incoming request)
- MinLat.py or MinDist.py (this is called by the server, it is the proper algorithm)
- test.py (a local test with a static request to check the algorithms)

To execute the algorithms, you have to run

python server.py

The server of MinLat runs on port 6161, the MinDist on port 6161.
