FROM balenalib/raspberrypi3:latest

RUN sudo apt-get update
RUN sudo apt-get upgrade -y
RUN sudo apt-get dist-upgrade -y
RUN sudo apt-get install wget
RUN sudo apt-get install build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev git

RUN wget https://www.python.org/ftp/python/3.6.5/Python-3.6.5.tar.xz && \
    tar xf Python-3.6.5.tar.xz && \
    rm -fr Python-3.6.5.tar.xz && \
    cd Python-3.6.5 && \
    ./configure && \
    make && \
    sudo make altinstall && \
    sudo make install

RUN python3 -m pip install pyserial
RUN python3 -m pip install azure-iothub-device-client
RUN sudo apt-get install libboost-python-dev

WORKDIR /app
COPY . /app
ENTRYPOINT [ "python3", "sample_2jciebu-iotsdk.py"]
