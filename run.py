#!/usr/bin/python
"""Wrapper script to run BWA."""
import os
import uuid
import time
import shutil
import logging
import argparse
from bwa_helpers import run_cmds
from bwa_helpers import combine_fastqs
from bwa_helpers import return_results
from bwa_helpers import exit_and_clean_up
from bwa_helpers import count_fastq_reads
from bwa_helpers import count_fasta_reads
from bwa_helpers import get_reads_from_url
from bwa_helpers import get_reference_database
from bwa_helpers import set_up_sra_cache_folder
from bwa_helpers import count_aliged_reads


def run_bwa(
    input_str=None,
    sample_name=None,
    ref_db=None,
    output_folder=None,
    threads=None,
    temp_folder="/share"
):
    # Make sure that there are no commas or whitespaces in the input
    assert ' ' not in input_str, input_str
    assert ',' not in input_str, input_str

    # Make a temporary folder for all files to be placed in
    temp_folder = os.path.join(temp_folder, str(uuid.uuid4())[:8])
    assert os.path.exists(temp_folder) is False
    os.mkdir(temp_folder)

    # Set up logging
    log_fp = os.path.join(temp_folder, "log.txt")
    logFormatter = logging.Formatter(
        '%(asctime)s %(levelname)-8s [BWA] %(message)s'
    )
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)

    # Write to file
    fileHandler = logging.FileHandler(log_fp)
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)
    # Also write to STDOUT
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

    # Keep track of the time elapsed to process this sample
    start_time = time.time()

    # Name the output file based on the input file
    # Ultimately adding ".json.gz" to the input file name
    if sample_name is not None:
        output_prefix = sample_name
    else:
        output_prefix = input_str[0].split("/")[-1]
    logging.info("Using sample name {} for output prefix".format(
        output_prefix))

    # Get the reference FASTA
    try:
        db_fp = get_reference_database(
            ref_db,
            temp_folder
        )
    except:
        exit_and_clean_up(temp_folder)
    logging.info("Reference database: " + db_fp)

    try:
        n_refs = count_fasta_reads(db_fp)
    except:
        raise Exception("Must specify FASTA reference")

    # Compile the BWA index for this FASTA input
    run_cmds([
        "bwa",
        "index",
        db_fp
    ])

    # Set up the NCBI fastq-dump cache folder within the temp folder
    set_up_sra_cache_folder(temp_folder)

    logging.info("Processing input argument: " + input_str)

    # Multiple input reads may be separated with a '+'
    input_str = input_str.split("+")
    # Make sure that they are all unique arguments
    assert len(input_str) == len(set(input_str)), "Duplicate arguments"
    # Make sure that the filenames are also all unique
    assert len(input_str) == len(set([
        s.split('/')[-1] for s in input_str
    ])), "Duplicate filenames"

    # Capture each command in a try statement
    # Get the input reads
    read_fps = []
    for s in input_str:
        logging.info("Fetching {}".format(s))
        try:
            read_fps.append(get_reads_from_url(
                s, temp_folder))
        except:
            exit_and_clean_up(temp_folder)

    # Combine the files into a single FASTQ
    read_fp = os.path.join(temp_folder, "input.fastq")
    combine_fastqs(read_fps, read_fp)

    # Write alignments in SAM format, then convert to BAM
    sam_fp = os.path.join(temp_folder, sample_name + ".sam")
    unsorted_bam_fp = os.path.join(temp_folder, sample_name + ".unsorted.bam")
    bam_fp = os.path.join(temp_folder, sample_name + ".bam")

    # Align the reads against the reference database
    run_cmds([
        "bwa",
        "mem",
        "-t",
        str(threads),
        "-o",
        sam_fp,
        db_fp,
        read_fp,
    ])

    # Convert to BAM
    run_cmds([
        "samtools",
        "view",
        "-F", "4",  # Remove unmapped reads
        "-o",
        unsorted_bam_fp,
        sam_fp
    ])
    os.unlink(sam_fp)
    # Sort the BAM file
    run_cmds([
        "samtools",
        "sort",
        "-o",
        bam_fp,
        unsorted_bam_fp
    ])
    assert os.path.exists(bam_fp)
    os.unlink(unsorted_bam_fp)

    # Count the total number of reads
    logging.info("Counting the total number of reads")
    n_reads = count_fastq_reads(read_fp)
    logging.info("Reads in input file: {:,}".format(n_reads))

    # Count the number of aligned reads
    logging.info("Counting the number of aligned reads")
    aligned_reads = count_aliged_reads(bam_fp)
    logging.info("Aligned reads: {:,}".format(aligned_reads))

    # Read in the logs
    logging.info("Reading in the logs")
    logs = open(log_fp, 'rt').readlines()

    # Wrap up all of the results into a single JSON
    # and write it to the output folder
    output = {
        "input_path": "+".join(input_str),
        "input": output_prefix,
        "sample": sample_name,
        "output_folder": output_folder,
        "logs": logs,
        "ref_db": db_fp,
        "ref_db_url": ref_db,
        "n_refs": n_refs,
        "total_reads": n_reads,
        "aligned_reads": aligned_reads,
        "time_elapsed": time.time() - start_time,
        "threads": threads
    }
    # Copy the alignment summary in JSON format
    return_results(
        output, output_prefix, output_folder, temp_folder, bam_fp
    )

    # Delete any files that were created for this sample
    logging.info("Removing temporary folder: " + temp_folder)
    shutil.rmtree(temp_folder)

    # Stop logging
    logging.info("Done")
    logging.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Align a set of reads with BWA.""")

    parser.add_argument("--input",
                        type=str,
                        help="""Location for input file(s). Multiple inputs joined by '+'.
                                (Supported: sra://, s3://, or ftp://).""")
    parser.add_argument("--sample-name",
                        type=str,
                        help="""Name of the sample (used to name the output files).""")
    parser.add_argument("--ref-db",
                        type=str,
                        help="""Folder containing reference database.
                                (Supported: s3://, ftp://, or local path).""")
    parser.add_argument("--output-folder",
                        type=str,
                        help="""Folder to place results.
                                (Supported: s3://, or local path).""")
    parser.add_argument("--threads",
                        type=int,
                        default=16,
                        help="Number of threads to use aligning.")
    parser.add_argument("--temp-folder",
                        type=str,
                        default='/share',
                        help="Folder used for temporary files.")

    args = parser.parse_args()

    run_bwa(
        input_str=args.input,
        sample_name=args.sample_name,
        ref_db=args.ref_db,
        output_folder=args.output_folder,
        threads=args.threads,
        temp_folder=args.temp_folder
    )
