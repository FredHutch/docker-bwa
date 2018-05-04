FROM ubuntu:16.04
MAINTAINER sminot@fredhutch.org

# Install prerequisites
RUN apt update && \
    apt-get install -y build-essential wget unzip python2.7 \
    python-dev git python-pip bats awscli curl \
    libcurl4-openssl-dev make gcc zlib1g-dev python3-pip

# Set the default langage to C
ENV LC_ALL C

# Use /share as the working directory
RUN mkdir /share
WORKDIR /share

# Add the bucket command wrapper, used to run code via sciluigi
RUN pip3 install bucket_command_wrapper==0.2.0 

# Install BWA
RUN mkdir /usr/bwa && \
    cd /usr/bwa && \
    wget https://github.com/lh3/bwa/releases/download/v0.7.17/bwa-0.7.17.tar.bz2 && \
    tar xvjf bwa-0.7.17.tar.bz2 && \
    cd bwa-0.7.17 && \
    make && \
    cp bwa /usr/local/bin

# Install python requirements
ADD requirements.txt /usr/bwa
RUN pip install -r /usr/bwa/requirements.txt && rm /usr/bwa/requirements.txt

# Install Samtools
RUN cd /usr/local/bin && \
    wget https://github.com/samtools/samtools/releases/download/1.7/samtools-1.7.tar.bz2 && \
    tar xvf samtools-1.7.tar.bz2 && \
    cd samtools-1.7 && \
    ./configure --without-curses --disable-lzma --disable-bz2 --prefix=/usr/local/bin && \
    make && \
    make install && \
    ln -s $PWD/samtools /usr/local/bin/

# Install the SRA toolkit
RUN cd /usr/local/bin && \
    wget -q https://ftp-trace.ncbi.nlm.nih.gov/sra/sdk/2.8.2/sratoolkit.2.8.2-ubuntu64.tar.gz && \
    tar xzf sratoolkit.2.8.2-ubuntu64.tar.gz && \
    ln -s /usr/local/bin/sratoolkit.2.8.2-ubuntu64/bin/* /usr/local/bin/ && \
    rm sratoolkit.2.8.2-ubuntu64.tar.gz

# Add the run script to the PATH
ADD . /usr/bwa/
RUN ln -s /usr/bwa/run.py /usr/local/bin/
ENV PYTHONPATH="/usr/bwa:${PYTHONPATH}"

# Run tests and then remove the folder
ADD tests /usr/bwa/tests
RUN bats /usr/bwa/tests/ && rm -r /usr/bwa/tests/