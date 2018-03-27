#!/usr/bin/env bats

@test "BWA 0.7.17" {
  v="$(bwa 2>&1 || true )"
  [[ "$v" =~ "0.7.17" ]]
}

@test "AWS CLI v1.11.146" {
  v="$(aws --version 2>&1)"
  [[ "$v" =~ "1.11.146" ]]
}

@test "Curl v7.47.0" {
  v="$(curl --version)"
  [[ "$v" =~ "7.47.0" ]]
}

@test "Samtools 1.7" {
  v="$(samtools --version)"
  [[ "$v" =~ "1.7" ]]
}

@test "fastq-dump" {
  [[ $(fastq-dump --stdout -X 2 SRR390728 && rm /root/ncbi/public/sra/SRR390728*) ]]
}

@test "Wrapper script" {
  v="$(run.py -h)"
  [[ "$v" =~ "Align a set of reads with BWA" ]]
}
