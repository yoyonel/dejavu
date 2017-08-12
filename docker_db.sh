#!/usr/bin/env bash

# retrieve SQL db configuration
source _tools.sh
get_db_config dejavu.cnf.SAMPLE

source set_env.sh

# Launch DB container
docker run \
	--rm \
	-d \
	--name $DEJAVU_DOCKER_DB_NAME \
	-e MYSQL_ROOT_PASSWORD=dejavu \
	-e MYSQL_DATABASE=dejavu \
	$DEJAVU_DOCKER_VOLUMES_FOR_DB \
	$DEJAVU_DOCKER_IMAGE_FOR_DB
