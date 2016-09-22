import logging
import os
import sys

import argparse

import _mypath
from bripipetools import postprocess

def parse_input_args(parser=None):
    parser.add_argument('-p', '--processed_project_path',
                        required=True,
                        default=None,
                        help=("path to processed directory - e.g., "
                              "/mnt/genomics/Illumina/"
                              "150218_D00565_0081_BC5UF5ANXX/"
                              "Project_P69Processed"))
    parser.add_argument('-t', '--output_type',
                        default=None,
                        choices=['c', 'm', 'b'],
                        help=("Select type of result file to combine: "
                              "c [counts], m [metrics], b [both]"))
    parser.add_argument('-d', '--debug',
                        action='store_true',
                        help=("Set logging level to debug"))

    # Parse and collect input arguments
    args = parser.parse_args()

    return parser.parse_args()

def main(argv):
    parser = argparse.ArgumentParser()
    args = parse_input_args(parser)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("combining output files for {} with option {}"
                .format(args.processed_project_path, args.output_type))

    if args.output_type == 'c' or args.output_type == 'b':
        logger.info("generating combined counts file")
        path = os.path.join(args.processed_project_path, 'counts')
        postprocess.OutputStitcher(path).write_table()

    if args.output_type == 'm' or args.output_type == 'b':
        logger.info("generating combined metrics file")
        path = os.path.join(args.processed_project_path, 'metrics')
        postprocess.OutputStitcher(path).write_table()

if __name__ == "__main__":
   main(sys.argv[1:])