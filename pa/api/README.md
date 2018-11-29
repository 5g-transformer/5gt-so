# API definition
This directory contains the YAML file to specify the PA API: `PA_API_defs.yaml`.

The API definition is done following swagger/OpenAPI version 2. Callback specifications are not available in this version, but they can be defined in OpenAPI 3 and are present in the `PA_API_defs.yaml` as comments.

## Python code generation with Docker
To generate the server stub, the swagger-codegen repository is included as a submodule under the directory `pa/api/swagger-codegen`.  Here we explain how to generate the code using docker, so there is no need to install maven, java and dependencies. So make sure you have docker installed and running before following the next steps:

```bash
git submodule init pa/api/swagger-codegen
git submodule update pa/api/swagger-codegen
cd pa/api/swagger-codegen
```
add the following line inside `run-in-docker.sh` to prevent SE linux labeling issues (in case your system uses SE linux):
```bash
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
./run-in-docker.sh mvn package
mkdir -p out/python-pa
cp ../PA_API_defs.yaml .
./run-in-docker.sh generate \ 
  -i PA_API_defs.yaml \                         
  -l python-flask \
  -o out/python-pa \
  -D supportPython2=true
```
this will produce the server stub under the directory `out/python-py`. To test that the server stub generation worked you can do the following:
```bash
cd out/python-pa
pip install -r requirements.txt
python -m swagger_server
```
This will start a server listening at http://0.0.0.0:8080/.

