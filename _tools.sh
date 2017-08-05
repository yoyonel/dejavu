#!/usr/bin/env bash

# https://stackoverflow.com/questions/1955505/parsing-json-with-unix-tools
function getJsonVal () { 
	# $1: JSON file
	# $2: Key to request
    result=$(cat $1 | python -c "import json,sys;sys.stdout.write(json.dumps(json.load(sys.stdin)$2))";)
    # https://stackoverflow.com/questions/9733338/shell-script-remove-first-and-last-quote-from-a-variable
    echo $result | tr -d '"'
}

function get_db_config() {
	# $1: JSON config db

	# https://stackoverflow.com/questions/1955505/parsing-json-with-unix-tools
	export PYTHONIOENCODING=utf8
	export DEJAVU_DB_USER=$(getJsonVal "$1" "['database']['user']")
	export DEJAVU_DB_PASSWORD=$(getJsonVal "$1" "['database']['passwd']")
	export DEJAVU_DB_HOST=$(getJsonVal "$1" "['database']['host']")
	export DEJAVU_DB_DB=$(getJsonVal "$1" "['database']['db']")
	# echo "DEJAVU_DB_USER: ${DEJAVU_DB_USER}"
	# echo "DEJAVU_DB_PASSWORD: ${DEJAVU_DB_PASSWORD}"
}