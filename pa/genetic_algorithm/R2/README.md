# A Genetic Algorithm for VNF placement (Release 2)

## Contents
- `ga`: Genetic algorithm core
- `ga_frontend.py`: REST-based frontend for executing the GA.
- `translator.py`: A module that translates between the internal and the common JSON input/output formats.
- `client.py`: Test client for the placement algorithms' REST API.
- `settings.conf`: Algorithm-specific configuration options and front end parameters.
- `PACompReq.json`: Test input for the GA.
- `requirements.txt`: Required python libraries.


## Requirements
The recommended way is to install and run everything inside a python virtual environment:

- Install the python virtualenv package: `pip install virtualenv`
- Create a virtual environment folder, e.g., /opt/venv
- Activate the virtual environment: . /opt/venv/bin/activate
- Install the necessary requirements: `pip install -r requirements.txt`

MongoDB should also be present in your system.


## Usage
- Start the front end server: `python ga_frontend.py -c ./settings.conf`
- Invoke the placement algorithm by executing the client: `python client.py -i ./PACompReq.json -o ./output.json`
If -o is not specified, the placement solution is output to stdout.


## Notes
- This release supports location and MEC constraints, and includes some changes in the internal operation of the GA (support for non-full-mesh host graphs, more initial feasibility checks, etc.)
- The front-end should receive a request whose body follows the common placement algorithm JSON format (R2). The request
is then translated by the front end to the internal input format, before it is passed on to the genetic algorithm
for execution.
- Two MongoDB database collections are maintained: One stores the input and the solution in the internal format,
and the other stores the information using the common JSON format. The front end takes care of synchronizing the 
records in the two collections; in both collections, a request is identified by the unique ID assigned by the caller (client).
- To control the internal operation of the algorithm, see the comments in settings.conf. Generally, a small
number of generations and a small solution pool make the algorithm terminate faster at the expense of solution quality.
- IP address, port and some other information are hardcoded in client.py. Please see the comments in the file
and set these parameters accordingly.

