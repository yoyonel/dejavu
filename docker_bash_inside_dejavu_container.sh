#!/usr/bin/env sh

# https://stackoverflow.com/questions/28721699/root-password-inside-a-docker-container
# http://fabiorehm.com/blog/2014/09/11/running-gui-apps-with-docker/

xhost +

docker run \
	-it --rm \
	--link dejavu-mysql:mysql \
	--entrypoint="bash" \
	-u 0 \
	-v $PWD:/home/dejavu \
	-e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
	dejavu:debian

xhost -