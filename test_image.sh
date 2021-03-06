#!/bin/bash

set -e

test_image(){
	
	img_tag=$1

	[[ "${#img_tag}" == "0" ]] && echo "Please specify image" && return

	[[ "$(docker run $img_tag echo True)" != "True" ]] && echo "Tag not found ($img_tag)" && return

	echo "TESTING SMALL LOCAL FILE"

	docker run \
		-v $PWD/tests:/share \
		--rm \
		$img_tag \
			run.py \
            --input /share/SRR6757151.100k.fastq.gz \
            --sample-name SRR6757151.100k.NC_002695.1 \
            --ref-db /share/NC_002695.1.fasta \
            --output-folder /share/output \
            --temp-folder /share/ \
            --threads 1

	echo "TESTING SMALL S3 FILE"

	docker run \
		--rm \
		-v ~/.aws/credentials:/root/.aws/credentials \
		$img_tag \
			run.py \
            --input s3://fh-pi-fredricks-d/lab/Sam_Minot/data/test/SRR6757151.100k.fastq.gz \
            --sample-name SRR6757151.100k.NC_002695.1 \
            --ref-db s3://fh-pi-fredricks-d/lab/Sam_Minot/data/test/NC_002695.1.fasta \
            --output-folder s3://fh-pi-fredricks-d/lab/Sam_Minot/data/test/bwa_output \
            --temp-folder /share/ \
            --threads 1
}

test_image $1

