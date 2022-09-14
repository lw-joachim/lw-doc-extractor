"""

"""

import argparse
import os
import logging
import k3logging
import sys

from lw_doc_extractor import __version__, primitive_doc_parser, doc_parser, story_compiler
import errno
import os
import json

__author__ = 'Joachim Kestner <kestner@lightword.de>'

logger = logging.getLogger(__name__)

def run_populator_main():
    
    parser = argparse.ArgumentParser(description="Actiry Populator"+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__))
    parser.add_argument("intput_file", help="The input document file")
    parser.add_argument("--server", default="server0185.articy.com", help="Server URL")
    parser.add_argument("--server_port", type=int, default=13170, help="Server Port")
    
    k3logging.set_parser_log_arguments(parser)

    parser.add_argument("--auth_file", help="File with username on first line and password on second line")
    
    
    
    args = parser.parse_args()
    
    # verboseFlag = ""
    # if(args.verbose):
    #     verboseFlag = "-v"
    # if(args.extra_verbose):
    #     verboseFlag = "-vv"
        
    sysargs = sys.argv[1:]
    

def _run_populator(ironPythonExePath, compilerOutputInputFile, verbosityFlag):
    os.system(f'start cmd /k "{ironPythonExePath}" "{compilerOutputInputFile} -vv')

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
            imgOutputPath = os.path.abspath(os.path.join(os.path.dirname(outputPath), "Images"))
            try:
                os.makedirs(os.path.dirname(imgOutputPath))
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                
        outputDirPath = os.path.dirname(outputPath)
        debugDirPath = os.path.join(outputDirPath, "debug")
        
        try:
            os.makedirs(debugDirPath)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        
        ast = doc_parser.parse(args.intput_file, imgOutputPath, debugDirPath)
        
        lexOutPath = os.path.join(debugDirPath,"lexer_output.json")
    
        with open(lexOutPath, "w") as fh:
            json.dump(ast, fh, indent=2)
        
        logger.info(f"Parsed and structured (lexing) output written to {lexOutPath}")
        
        resultJson = story_compiler.compile_story(ast)
        
        logger.info(f"Compilation complete")
        
        with open(outputPath, "w") as fh:
            json.dump(resultJson, fh, indent=2)
            
        logger.info(f"Final (compiled) output written to {outputPath}")
