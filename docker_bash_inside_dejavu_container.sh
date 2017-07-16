#!/usr/bin/env sh

# https://stackoverflow.com/questions/28721699/root-password-inside-a-docker-container
docker run \
	-it --rm \
	--link dejavu-mysql:mysql \
	--entrypoint="bash" \
	-u 0 \
	-v $PWD:/home/dejavu/mount \
	dejavu:debian
