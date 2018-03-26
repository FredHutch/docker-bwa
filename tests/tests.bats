#!/usr/bin/env bats

@test "BWA 0.7.17" {
  v="$(bwa 2>&1 || true )"
  [[ "$v" =~ "0.7.17" ]]
}

@test "Wrapper script" {
  v="$(run.py -h)"
  [[ "$v" =~ "Align a set of reads with BWA" ]]
}
