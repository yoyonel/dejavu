#!/usr/bin/env bash
#####################################
### Dejavu example testing script ###
#####################################

set -e

###########
# Clear out previous results
rm -rf ./results_video ./temp_video

###########
# Fingerprint files of extension mp3 in the ./mp3 folder
python dejavu.py -f ./mp4/ mp4

##########
# Run a test suite on the ./mp3 folder by extracting 1, 2, 3, 4, and 5
# second clips sampled randomly from within each song 8 seconds
# away from start or end, sampling with random seed = 42, and finally
# store results in ./results and log to dejavu-test.log
#PYTHON_DBG="-m pudb.run"
PYTHON_DBG=""
python ${PYTHON_DBG} run_tests.py \
    --video \
	--secs 5 \
	--temp ./temp_video \
	--log-file ./results/dejavu-test-video.log \
	--padding 8 \
	--seed 42 \
	--results ./results_video \
	./mp4

set +e

reset