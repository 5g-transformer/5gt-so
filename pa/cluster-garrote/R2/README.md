# Cluster-garrote PA
In this readme you can find information on:
 * how to generate the server stub
 * how to run the server stub in a python virtualenv

## Server stub code generation with Docker
To generate the server stub, the swagger-codegen repository is included as a submodule under the directory `pa/api/swagger-codegen`.  Here we explain how to generate the server stub code using docker.

That way, there is no need to install maven, java and dependencies. So make sure you have docker installed and running before following the next steps:

```bash
# Get the swagger code generation submodule
git submodule init pa/api/swagger-codegen
git submodule update pa/api/swagger-codegen
cd pa/api/swagger-codegen
```
add the following line inside `run-in-docker.sh` to prevent SE linux labeling issues (in case your system uses SE linux):
```bash
# inside run-in-docker.sh
# ...
docker run --rm -it \
        -w /gen \
        -e GEN_DIR=/gen \
        -e MAVEN_CONFIG=/var/maven/.m2 \
        -u "$(id -u):$(id -g)" \
        -v "${PWD}:/gen" \
        -v "${maven_cache_repo}:/var/maven/.m2/repository" \
        --entrypoint /gen/docker-entrypoint.sh \
        --security-opt label=disable \  # <====== ADD THIS LINE
        maven:3-jdk-7 "$@"
# ...
```
Once the file is modified, just run it to package and generate the python flask server stub with the following commands:
```bash
# create the package
./run-in-docker.sh mvn package
# generate the server stub under ../../cluster-garrote/R2/rest-api-server/
cp ../PA_API_defs.yaml .
./run-in-docker.sh generate \ 
  -i PA_API_defs.yaml \                         
  -l python-flask \
  -o ../../cluster-garrote/R2/rest-api-server/ \
  -D supportPython2=true
```

## Running the server
Be sure you have `pip2` and `virtualenv` installed before continuing.

Probably you don't have the generator and networkx_fork submodule inside R2 of cluster-garrote, hence execute this to prevent errors:
```bash
cd ../../..
git submodule init 
git submodule update 
```

Then you need to create a python virtual environment inside the REST server stub, and install the required dependencies:

```bash
$ cd pa/cluster-garrote/R2/rest-api-server/
$ cd pa/cluster-garrote/R2/rest-api-server/
$ virtualenv env --python=python2
$ source env/bin/activate
(env) $ pip2 install -r requirements.txt
(env) $ pip2 install -r pa_reqs.txt
```

Next step is specifying the port where the server will listen. Modify the line inside `pa/cluster-garrote/R2/rest-api-server/swagger_server/__main__.py` where port number is specified.

To test that the server stub generation worked you can do the following:
```bash
(env) $ python -m swagger_server
```
This will start a server listening at http://0.0.0.0:PORT/ .


