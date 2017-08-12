#!/usr/bin/env bash

set -e 

source set_env.sh

# Launch Database container
./docker_db.sh

xhost +

# DOCKER_USER=root
DOCKER_USER=0

docker run \
    -it --rm \
    -u $DOCKER_USER \
    $DOCKER_SHARE_DISPLAY \
    -v $PWD:/home/dejavu \
	--link $DEJAVU_DOCKER_DB_NAME:mysql \
    --entrypoint="/bin/bash" \
    ${DEJAVU_DOCKER_IMAGE}

xhost -

docker stop dejavu-mysql

set +e