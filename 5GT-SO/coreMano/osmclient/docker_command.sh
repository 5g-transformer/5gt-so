#!/bin/sh
#helper routine that creates user/group in docker container
#necessary when using volumes and inputing -user into docker run
groupadd -o -g $(id -g) -r $2
useradd -o -u $(id -u) --create-home -r -g  $2 $1
shift 2
exec $@
