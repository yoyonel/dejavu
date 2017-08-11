#!/usr/bin/env bash

# retrieve SQL db configuration
source _tools.sh
get_db_config dejavu.cnf.SAMPLE

# MySQL
# DOCKER_IMAGE_DB=mysql:latest
#DOCKER_DB_VOLUMES=-v $(realpath ./database):/var/lib/mysql \

# MariaDB
mkdir -p ./mariadb
DOCKER_IMAGE_DB=mariadb:latest
DOCKER_DB_VOLUMES="-v $(realpath ./mariadb):/var/lib/mysql"

# Launch DB container
docker run \
	--rm \
	-d \
	--name dejavu-mysql \
	-e MYSQL_ROOT_PASSWORD=dejavu \
	-e MYSQL_DATABASE=dejavu \
	$DOCKER_DB_VOLUMES \
	$DOCKER_IMAGE_DB
