"""

"""

import argparse
import os
import logging
import k3logging

from lw_doc_extractor import __version__, primitive_doc_parser, doc_parser

__author__ = 'Joachim Kestner <kestner@lightword.de>'

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description=__doc__+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=argparse.RawDescriptionHelpFormatter)
    # parser.add_argument("-f", "--flag", action="store_true", help="Example argparse of a choice")
    # parser.add_argument("-c", "--choice", default="c1", choices=["c1", "c2", "c3", "c4"], help="Example of an argparse choice argument")
    # parser.add_argument("-o", "--optional", help="Example of an optional flag with an argument")
    parser.add_argument("intput_file", help="The input document file")
    parser.add_argument("-o", "--output", default="out.json", help="The output file path")
    parser.add_argument("--output_images", help="If set will save the images into this directory, else a directory will be created next to the output json")
    parser.add_argument("--primitive", action="store_true", help="Use the old/primitive parsing algorithm")
    
    k3logging.set_parser_log_arguments(parser)
    
    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
        
    
    
    if args.primitive:
        primitive_doc_parser.parse(args.intput_file, args.output)
    else:
        outputPath = os.path.abspath(args.output)
        if args.output_images:
            imgOutputPath = os.path.abspath(args.output_images)
        else:
            imgOutputPath = os.path.join(os.path.dirname(outputPath), "Images")
            try:
                os.makedirs(directory)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            os.mkdir(imgOutputPath, mode, dir_fd=None)
            
        
        doc_parser.parse(args.intput_file, outputPath, imgOutputPath, None)
