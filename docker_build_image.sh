#!/usr/bin/env bash

source set_env.sh

cd docker

docker build \
	-t ${DEJAVU_DOCKER_IMAGE} \
	.
cd -
