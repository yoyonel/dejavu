#!/usr/bin/env bash

ffprobe -v error -show_streams $1 | grep codec_type
