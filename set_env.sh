#!/usr/bin/env bash

DEJAVU_DOCKER_IMAGE=dejavu:u16.04_opencv3.1

# MySQL
# mkdir -p ./database
# DEJAVU_DOCKER_IMAGE_FOR_DB=mysql:latest
# DEJAVU_DOCKER_VOLUMES_FOR_DB=-v $(realpath ./database):/var/lib/mysql \

# MariaDB
mkdir -p ./mariadb
DEJAVU_DOCKER_IMAGE_FOR_DB=mariadb:latest
DEJAVU_DOCKER_VOLUMES_FOR_DB="-v $(realpath ./mariadb):/var/lib/mysql"

DEJAVU_DOCKER_DB_NAME=dejavu-mysql


#
DOCKER_SHARE_DISPLAY="-e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix"