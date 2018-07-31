FROM fedora:27

RUN dnf update -y
RUN dnf install psmisc which vim curl git mnemosyne gvim -y

# Install Mnemosyne libraries both system-wide and to virtualenv
RUN mnemosyne --version

# Setup language environment
ENV LC_ALL en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8

# Setup vimwiki
RUN mkdir -p /root/.vim/bundle /root/.vim/autoload
RUN curl -LSso ~/.vim/autoload/pathogen.vim https://tpo.pe/pathogen.vim
RUN cd /root/.vim/bundle; git clone https://github.com/vimwiki/vimwiki.git
RUN cd /root/.vim/bundle/vimwiki/; git checkout dev

# Setup knowledge
ADD requirements.txt requirements.txt
RUN pip3 install vimrunner nose pytest coveralls coverage
RUN pip3 install -r requirements.txt
RUN mkdir -p /root/.vim/bundle/knowledge
WORKDIR /root/.vim/bundle/knowledge

CMD ["sh", "-c", "python3 -m pytest -vv tests/"]
