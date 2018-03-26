FROM ubuntu:16.04
MAINTAINER sminot@fredhutch.org

# Install prerequisites
RUN apt update && \
    apt-get install -y build-essential wget unzip python2.7 \
    python-dev git python-pip bats awscli curl \
    libcurl4-openssl-dev make gcc zlib1g-dev

# Set the default langage to C
ENV LC_ALL C

# Use /share as the working directory
RUN mkdir /share
WORKDIR /share

# Install BWA
RUN mkdir /usr/bwa && \
    cd /usr/bwa && \
    wget https://github.com/lh3/bwa/releases/download/v0.7.17/bwa-0.7.17.tar.bz2 && \
    tar xvjf bwa-0.7.17.tar.bz2 && \
    cd bwa-0.7.17 && \
    make && \
    cp bwa /usr/local/bin

# Add the run script to the PATH
ADD run.py /usr/local/bin/

# Run tests and then remove the folder
ADD tests /usr/bwa/tests
RUN bats /usr/bwa/tests/ && rm -r /usr/bwa/tests/