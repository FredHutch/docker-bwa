# Docker-BWA
Docker image running BWA

In addition to BWA, this image contains a wrapper script that 
executes the following tasks in a single command:

  1. Download a reference index (or access a local file)
  2. Download a set of reads in FASTQ format (or access a local file)
  3. Align reads against the reference
  4. Record logs and runtime information
  5. Write alignments and summary file to a local or remote folder
