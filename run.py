#!/usr/bin/python
"""Wrapper script to run BWA."""
import argparse


def run_bwa(
    input=None,
    ref_db=None,
    output_folder=None,
    threads=None,
    temp_folder="/share"
):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Align a set of reads with BWA.""")

    parser.add_argument("--input",
                        type=str,
                        help="""Location for input file(s). Multiple inputs joined by '+'.
                                (Supported: sra://, s3://, or ftp://).""")
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
        input=args.input,
        ref_db=args.ref_db,
        output_folder=args.output_folder,
        threads=args.threads,
        temp_folder=args.temp_folder
    )