#!/usr/bin/python
import os
import sys
import gzip
import json
import uuid
import shutil
import logging
import traceback
import subprocess
from Bio.SeqIO.FastaIO import SimpleFastaParser
from Bio.SeqIO.QualityIO import FastqGeneralIterator


def run_cmds(commands, retry=0, catchExcept=False, stdout=None):
    """Run commands and write out the log, combining STDOUT & STDERR."""
    logging.info("Commands:")
    logging.info(' '.join(commands))
    if stdout is None:
        p = subprocess.Popen(commands,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        stdout, stderr = p.communicate()
    else:
        with open(stdout, "wt") as fo:
            p = subprocess.Popen(commands,
                                 stderr=subprocess.PIPE,
                                 stdout=fo)
            stdout, stderr = p.communicate()
        stdout = False
    exitcode = p.wait()
    if stdout:
        logging.info("Standard output of subprocess:")
        for line in stdout.split('\n'):
            logging.info(line)
    if stderr:
        logging.info("Standard error of subprocess:")
        for line in stderr.split('\n'):
            logging.info(line)

    # Check the exit code
    if exitcode != 0 and retry > 0:
        msg = "Exit code {}, retrying {} more times".format(exitcode, retry)
        logging.info(msg)
        run_cmds(commands, retry=retry - 1)
    elif exitcode != 0 and catchExcept:
        msg = "Exit code was {}, but we will continue anyway"
        logging.info(msg.format(exitcode))
    else:
        assert exitcode == 0, "Exit code {}".format(exitcode)


def get_reference_database(ref_db, temp_folder):
    """Get a reference FASTA."""

    # Get files from AWS S3
    if ref_db.startswith('s3://'):
        logging.info("Getting reference database from S3: " + ref_db)

        # Save the database to the local temp folder
        local_fp = os.path.join(
            temp_folder,
            ref_db.split('/')[-1]
        )

        assert os.path.exists(local_fp) is False

        logging.info("Saving database to " + local_fp)
        run_cmds([
            'aws',
            's3',
            'cp',
            '--quiet',
            '--sse',
            'AES256',
            ref_db,
            local_fp
        ])


    else:
        # Treat the input as a local path
        logging.info("Getting reference database from local path: " + ref_db)

        assert os.path.exists(ref_db)

        local_fp = ref_db

    if local_fp.endswith(".gz"):
        logging.info("Decompressing reference FASTA")
        with open(local_fp[:-3], "wt") as fo:
            run_cmds([
                "gunzip",
                "-c",
                local_fp
            ], 
            stdout=fo)
        local_fp = local_fp[:-3]

    return local_fp


def exit_and_clean_up(temp_folder):
    """Log the error messages and delete the temporary folder."""
    # Capture the traceback
    logging.info("There was an unexpected failure")
    exc_type, exc_value, exc_traceback = sys.exc_info()
    for line in traceback.format_tb(exc_traceback):
        logging.info(line)

    # Delete any files that were created for this sample
    logging.info("Removing temporary folder: " + temp_folder)
    shutil.rmtree(temp_folder)

    # Exit
    logging.info("Exit type: {}".format(exc_type))
    logging.info("Exit code: {}".format(exc_value))
    sys.exit(exc_value)


def set_up_sra_cache_folder(temp_folder):
    """Set up the fastq-dump cache folder within the temp folder."""
    logging.info("Setting up fastq-dump cache within {}".format(temp_folder))
    for path in [
        "/root/ncbi",
        "/root/ncbi/public"
    ]:
        if os.path.exists(path) is False:
            os.mkdir(path)

    if os.path.exists("/root/ncbi/public/sra"):
        shutil.rmtree("/root/ncbi/public/sra")

    # Now make a folder within the temp folder
    temp_cache = os.path.join(temp_folder, "sra")
    assert os.path.exists(temp_cache) is False
    os.mkdir(temp_cache)

    # Symlink it to /root/ncbi/public/sra/
    run_cmds(["ln", "-s", "-f", temp_cache, "/root/ncbi/public/sra"])

    assert os.path.exists("/root/ncbi/public/sra")


def get_reads_from_url(
    input_str,
    temp_folder,
    random_string=str(uuid.uuid4())[:8]
):
    """Get a set of reads from a URL -- return the downloaded filepath."""
    # Fetch reads into $temp_folder/fetched_reads/
    fetched_reads_folder = os.path.join(temp_folder, "fetched_reads")

    if not os.path.exists(fetched_reads_folder):
        logging.info("Making new folder {}".format(fetched_reads_folder))
        os.mkdir(fetched_reads_folder)

    logging.info("Getting reads from {}".format(input_str))

    filename = input_str.split('/')[-1]
    local_path = os.path.join(fetched_reads_folder, filename)

    logging.info("Filename: " + filename)
    logging.info("Local path: " + local_path)

    if not input_str.startswith(('s3://', 'sra://', 'ftp://')):
        logging.info("Treating as local path")
        msg = "Input file does not exist ({})".format(input_str)
        assert os.path.exists(input_str), msg

        logging.info("Making a symlink to temporary folder")
        os.symlink(input_str, local_path)

    # Get files from AWS S3
    elif input_str.startswith('s3://'):
        logging.info("Getting reads from S3")
        run_cmds([
            'aws', 's3', 'cp', '--quiet', '--sse',
            'AES256', input_str, fetched_reads_folder
            ])

    # Get files from an FTP server
    elif input_str.startswith('ftp://'):
        logging.info("Getting reads from FTP")
        run_cmds(['wget', '-P', fetched_reads_folder, input_str])

    # Get files from SRA
    elif input_str.startswith('sra://'):
        accession = filename
        logging.info("Getting reads from SRA: " + accession)
        local_path = get_sra(accession, fetched_reads_folder)

    else:
        raise Exception("Did not recognize prefix for input: " + input_str)

    return local_path


def get_sra(accession, temp_folder):
    """Get the FASTQ for an SRA accession."""
    logging.info("Downloading {} from SRA".format(accession))

    local_path = os.path.join(temp_folder, accession + ".fastq")
    logging.info("Local path: {}".format(local_path))

    # Download via fastq-dump
    logging.info("Downloading via fastq-dump")
    run_cmds([
        "prefetch", accession
    ])
    run_cmds([
        "fastq-dump",
        "--split-files",
        "--outdir",
        temp_folder, accession
    ])

    # Make sure that some files were created
    msg = "File could not be downloaded from SRA: {}".format(accession)
    assert any([
        fp.startswith(accession) and fp.endswith("fastq")
        for fp in os.listdir(temp_folder)
    ]), msg

    # Combine any multiple files that were found
    logging.info("Concatenating output files")
    with open(local_path + ".temp", "wt") as fo:
        cmd = "cat {}/{}*fastq".format(temp_folder, accession)
        cat = subprocess.Popen(cmd, shell=True, stdout=fo)
        cat.wait()

    # Remove the temp files
    for fp in os.listdir(temp_folder):
        if fp.startswith(accession) and fp.endswith("fastq"):
            fp = os.path.join(temp_folder, fp)
            logging.info("Removing {}".format(fp))
            os.unlink(fp)

    # Remove the cache file, if any
    cache_fp = "/root/ncbi/public/sra/{}.sra".format(accession)
    if os.path.exists(cache_fp):
        logging.info("Removing {}".format(cache_fp))
        os.unlink(cache_fp)

    # Clean up the FASTQ headers for the downloaded file
    run_cmds(["mv", local_path + ".temp", local_path])

    # Return the path to the file
    logging.info("Done fetching " + accession)
    return local_path


def count_fasta_reads(fp):
    n = 0
    if fp.endswith(".gz"):
        with gzip.open(fp, "rt") as f:
            for record in SimpleFastaParser(f):
                n += 1
    else:
        with open(fp, "rt") as f:
            for record in SimpleFastaParser(f):
                n += 1

    return n


def count_fastq_reads(fp):
    n = 0
    if fp.endswith(".gz"):
        f = gzip.open(fp, "rt")
    else:
        f = open(fp, "rt")

    for line_ix, line in enumerate(f):
        if line_ix % 4 == 0:
            if line[0] == '@':
                n += 1
            else:
                f.close()
                logging.info("Not in FASTQ format, trying FASTA")
                return count_fasta_reads(fp)
    f.close()

    # If no reads were found, try counting it as a FASTA
    if n == 0:
        logging.info("No FASTQ reads found, trying to read as FASTA")
        return count_fasta_reads(fp)
    else:
        return n

def combine_fastqs(fps_in, fp_out):
    """Combine multiple FASTQs into a single FASTQ."""
    assert len(fps_in) > 0

    if len(fps_in) == 1:
        assert os.path.exists(fps_in[0])
        logging.info("Making a symlink: {} -> {}".format(fps_in[0], fp_out))
        os.symlink(fps_in[0], fp_out)
    else:
        logging.info("Combining {:,} FASTQ files".format(len(fps_in)))
        logging.info("Writing all inputs to {}".format(fp_out))
        with open(fp_out, "wt") as fo:
            for fp_ix, f in enumerate(fps_in):
                logging.info("Adding {} to {}".format(f, fp_out))
                with open(f, "rt") as fi:
                    for line_ix, line in enumerate(fi):
                        # Add a file index to the header
                        # In case there are two files with the same headers
                        mod = line_ix % 4
                        if mod == 0 or mod == 2:
                            line = line.rstrip("\n")
                            fo.write("{}-{}\n".format(line, fp_ix))
                        else:
                            fo.write(line)


def return_results(out, read_prefix, output_folder, temp_folder, bam_fp):
    """Write out the final results as a JSON object."""
    # Make a temporary file
    temp_fp = os.path.join(temp_folder, read_prefix + '.json')
    with open(temp_fp, 'wt') as fo:
        json.dump(out, fo)

    # Compress the output
    run_cmds(['gzip', temp_fp])
    temp_fp = temp_fp + '.gz'

    if output_folder.startswith('s3://'):
        # Copy to S3
        run_cmds([
            'aws',
            's3',
            'cp',
            '--quiet',
            '--sse',
            'AES256',
            temp_fp,
            output_folder])
        os.unlink(temp_fp)

        run_cmds([
            'aws',
            's3',
            'cp',
            '--quiet',
            '--sse',
            'AES256',
            bam_fp,
            output_folder])
        os.unlink(bam_fp)
    else:
        # Copy to local folder
        run_cmds(['mv', temp_fp, output_folder])
        run_cmds(['mv', bam_fp, output_folder])
