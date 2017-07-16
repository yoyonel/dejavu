#!/usr/bin/env sh

docker run \
	--rm \
	--name dejavu-mysql \
	-e MYSQL_ROOT_PASSWORD=dejavu \
	-e MYSQL_DATABASE=dejavu \
	-d \
	-v $(realpath ./database):/var/lib/mysql \
	mysql:latest
