#!/usr/bin/env bash
#####################################
### Dejavu example testing script ###
#####################################

set -e

###########
# Clear out previous results
rm -rf ./results_video ./temp_video

###########
# Fingerprint files of extension mp4 in the ./mp4 folder
python dejavu.py -f ./videos/ mp4

##########
# Run a test suite on the ./mp4 folder by extracting 1, 2, 3, 4, and 5
# second clips sampled randomly from within each song 3 seconds
# away from start or end, sampling with random seed = 42, and finally
# store results in ./results_video and log to dejavu-test.log
#PYTHON_DBG="-m pudb.run"
#--skip-generate-test-files \
PYTHON_DBG=""
python ${PYTHON_DBG} run_tests.py \
    --video \
	--secs 5 \
	--temp ./temp_video \
	--keep-temp \
	--log-file ./results_video/dejavu-test-video.log \
	--padding 3 \
	--seed 42 \
	--results ./results_video \
	./videos

set +e

reset