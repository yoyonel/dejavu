# FROM jrottenberg/ffmpeg:ubuntu
# FROM latty/screenpulse/ffmpeg:cu-3.3
# FROM latty/opencv-3.1.0:ubuntu
FROM yoyonel/ffmpeg:opencv

RUN apt-get update && \
	apt-get install -y \
			python-pip \
			portaudio19-dev

ADD ./requirements.txt requirements.txt

# RUN pip install virtualenv && \
#     virtualenv --system-site-packages env_with_system && \
#     pip install -r requirements.txt
RUN pip install --upgrade pip && \
	pip install -r requirements.txt

# https://stackoverflow.com/questions/5178292/pip-install-mysql-python-fails-with-environmenterror-mysql-config-not-found
# 
RUN apt-get update && \
	apt-get install -y \
			python-mysqldb \
			python-tk

# Installation de ZSH
ENV TERM xterm-256color

# url: https://hub.docker.com/r/bwithem/oh-my-zsh-tmux/~/dockerfile/
RUN apt-get install -y \
			git \
			curl

RUN pip install ipython

ADD wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

RUN apt-get update && \
	apt-get install -y \
		mysql-client

ADD test_dejavu.sh /home/dejavu/test_dejavu.sh
RUN chmod +x /home/dejavu/test_dejavu.sh

RUN git clone --depth=1 https://github.com/Bash-it/bash-it.git ~/.bash_it &&\
	~/.bash_it/install.sh --silent

# https://stackoverflow.com/questions/27701930/add-user-to-docker-container
RUN useradd -ms /bin/bash dejavu
USER dejavu

WORKDIR /home/dejavu
