#!/usr/bin/env sh

set -e 

# Launch Database container
./docker_db.sh

xhost +

docker run \
    -it --rm \
    -u 0 \
    -v $PWD:/home/dejavu \
    -e DISPLAY=$DISPLAY \
	-v /tmp/.X11-unix:/tmp/.X11-unix \
	--link dejavu-mysql:mysql \
    --entrypoint="/bin/bash" \
    dejavu:debian

xhost -

docker stop dejavu-mysql

set +e