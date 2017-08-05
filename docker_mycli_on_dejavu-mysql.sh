#!/usr/bin/env bash

source _tools.sh

get_db_config dejavu.cnf.SAMPLE

CONTAINER_DB_DEJAVU=dejavu-mysql
DOCKER_IMAGE_MYCLI=diyan/mycli

docker run \
	--rm -ti \
	--name=mycli \
	--link=$CONTAINER_DB_DEJAVU:mysql \
	$DOCKER_IMAGE_MYCLI \
	--host=$DEJAVU_DB_HOST \
	--database=$DEJAVU_DB_DB \
	--user=$DEJAVU_DB_USER \
	--password=$DEJAVU_DB_PASSWORD

