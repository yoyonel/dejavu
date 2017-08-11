#!/usr/bin/env sh

set -e 

# Launch Database container
./docker_db.sh

xhost +

# DOCKER_USER=root
DOCKER_USER=0

docker run \
    -it --rm \
    -u $DOCKER_USER \
    -v $PWD:/home/dejavu \
    -e DISPLAY=$DISPLAY \
	-v /tmp/.X11-unix:/tmp/.X11-unix \
	--link dejavu-mysql:mysql \
    --entrypoint="/bin/bash" \
    dejavu:debian

xhost -

docker stop dejavu-mysql

set +e