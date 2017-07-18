FROM jrottenberg/ffmpeg:ubuntu

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
RUN apt-get install -y \
			python-mysqldb \
			python-tk

# Installation de ZSH
ENV TERM xterm-256color

# url: https://hub.docker.com/r/bwithem/oh-my-zsh-tmux/~/dockerfile/
RUN apt-get install -y \
			git \
			curl \
			zsh tmux

################## BEGIN INSTALLATION ######################
RUN git clone git://github.com/bwithem/oh-my-zsh.git ~/.oh-my-zsh \
    && cp ~/.oh-my-zsh/templates/zshrc.zsh-template ~/.zshrc \
    && chsh -s /bin/zsh


RUN pip install ipython


# https://stackoverflow.com/questions/27701930/add-user-to-docker-container
RUN useradd -ms /bin/bash dejavu
USER dejavu
WORKDIR /home/dejavu

ENTRYPOINT ["zsh"]