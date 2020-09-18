ARG PYTHON_VERSION=3.8
ARG VIM_VERSION=v8.2.0716
ARG ANKI_VERSION=2.1.33
ARG MNEMOSYNE_VERSION=master
ARG VIMWIKI_VERSION=master

FROM python:${PYTHON_VERSION}

# Configure locale to ensure UTF-8 works correctly
RUN apt-get update && apt-get -y install locales
RUN echo "en_US UTF-8" >> /etc/locale.gen
RUN locale-gen
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8

# Install vim
RUN apt-get update && apt-get -y install \
    gcc \
    git \
    make \
    libxt-dev \
    libgtk-3-dev \
    ncurses-dev && \
    apt-get clean
ARG VIM_VERSION
RUN git clone --depth 1 --recurse-submodules --shallow-submodules \
    --branch $VIM_VERSION https://github.com/vim/vim /usr/src/vim
WORKDIR /usr/src/vim
# "backport" https://github.com/vim/vim/commit/16d7eced1a08565a9837db8067c7b9db5ed68854
RUN sed -i -e '/#\s*undef _POSIX_THREADS/d' src/if_python3.c
RUN ./configure --prefix=/opt/vim --enable-pythoninterp --enable-python3interp --enable-gui=gtk3
RUN make -j$(nproc)
RUN make install

# Install test dependencies
RUN apt-get install \
    git \
    gcc
RUN pip install \
    coverage \
    coveralls \
    pytest \
    pytest-cov \
    pytest-xdist \
    https://github.com/liskin/vimrunner-python/archive/8c19ff88050c09236e7519425bfae33c687483df.zip
COPY requirements.txt /tmp/knowledge/requirements.txt
RUN pip install -r /tmp/knowledge/requirements.txt

RUN apt-get update && \
    apt-get -y install \
        make \
        psmisc \
        xvfb && \
    apt-get clean
RUN ln -sf /usr/share/zoneinfo/Etc/UTC /etc/localtime

# Install mnemosyne
RUN mkdir /opt/mnemosyne/
WORKDIR /opt/mnemosyne/
ARG MNEMOSYNE_VERSION
RUN wget https://github.com/mnemosyne-proj/mnemosyne/archive/${MNEMOSYNE_VERSION}.zip && \
    unzip ${MNEMOSYNE_VERSION}.zip && \
    rm ${MNEMOSYNE_VERSION}.zip
WORKDIR /opt/mnemosyne/mnemosyne-${MNEMOSYNE_VERSION}
RUN pip3 install -r requirements.txt && \
    pip3 install googletrans gtts && \
    python3 setup.py install

# Install Anki
ARG ANKI_VERSION
RUN pip install \
    aqt==${ANKI_VERSION} \
    anki==${ANKI_VERSION} \
    ankirspy==${ANKI_VERSION} \
    pyqt5 pyqtwebengine

# install runtime deps of vim/knowledge
RUN apt-get install -y libgtk-3-0
ENV PATH=/opt/vim/bin:$PATH
RUN vim --version

ARG VIMWIKI_VERSION
RUN git clone --depth 1 --recurse-submodules --shallow-submodules \
    --branch $VIMWIKI_VERSION https://github.com/vimwiki/vimwiki /root/.vim/bundle/vimwiki

WORKDIR /root/.vim/bundle/knowledge
