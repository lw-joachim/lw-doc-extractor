"""

"""

import argparse
import os
import logging
import k3logging

from lw_doc_extractor import __version__, doc_extractor

__author__ = 'Joachim Kestner <kestner@lightword.de>'

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description=__doc__+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=argparse.RawDescriptionHelpFormatter)
    # parser.add_argument("-f", "--flag", action="store_true", help="Example argparse of a choice")
    # parser.add_argument("-c", "--choice", default="c1", choices=["c1", "c2", "c3", "c4"], help="Example of an argparse choice argument")
    # parser.add_argument("-o", "--optional", help="Example of an optional flag with an argument")
    parser.add_argument("intput_file", help="The input document file")
    
    k3logging.set_parser_log_arguments(parser)
    
    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
    
    
    for arg in vars(args):
        print("{}: {}".format(arg, getattr(args, arg)))
        
    
    
    # call the actual 'business' logic here
    # Note: Having the main logic within a library enables another project to use
    # the implemented functionalities directly through importing the installed library
    doc_extractor.do_something(args.intput_file)
