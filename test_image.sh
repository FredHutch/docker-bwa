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
            --sample-name SRR6757151.100k \
            --ref-db /share/NC_002695.1.fasta \
            --output-folder /share/ \
            --temp-folder /share/ \
            --threads 1

}

test_image $1

