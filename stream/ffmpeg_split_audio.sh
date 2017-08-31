ffmpeg -fflags +genpts -i "../mp3/Brad-Sucks--Total-Breakdown.mp3" \
-map 0 -vn -c copy -f segment -segment_format mp3 \
-segment_time 5 -segment_list audio.ffcat -reset_timestamps 1 \
-v error chunk-%03d.mp3
