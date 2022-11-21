"""

"""

import argparse
import os
import logging
import k3logging
import sys
import subprocess

from lw_doc_extractor import __version__, doc_parser, story_compiler
from lw_doc_extractor.old import primitive_doc_parser
import errno
import os
import json
from argparse import RawDescriptionHelpFormatter, ArgumentDefaultsHelpFormatter

__author__ = 'Joachim Kestner <kestner@lightword.de>'

logger = logging.getLogger(__name__)

_POP_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resources", "articy_populator.py"))

def run_populator_main():
    
    parser = argparse.ArgumentParser(description="Actiry Populator"+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("input_file", help="The input json file")
    parser.add_argument("--server", default="server0185.articy.com", help="Server URL")
    parser.add_argument("--server_port", type=int, default=13170, help="Server Port")
    parser.add_argument("--project", default="api_test_proj", help="The name of the project to import to")
    parser.add_argument("--auth_file", help="File with username on first line and password on second line")
    parser.add_argument("--iron_python", default=r"C:\Program Files\IronPython 2.7\ipy.exe", help="Iron python path. NOTE: Articy.MetaModel.xml needs to have been transferred.")
    parser.add_argument("--articy_api_lib", default=r"C:\soft\articy_draft_API", help="Path to articy api installation")
    
    k3logging.set_parser_log_arguments(parser)

    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
    
    verboseFlag = ""
    if(args.verbose):
        verboseFlag = "-v"
    if(args.extra_verbose):
        verboseFlag = "-vv"
        
    _run_populator(args.input_file, args.project, verboseFlag, args.iron_python, args.server,args.server_port, args.auth_file, args.articy_api_lib )
    

def _run_populator(compilerOutputInputFile, project="api_test_proj", verbosityFlag="-v", ironPythonExePath=r"C:\Program Files\IronPython 2.7\ipy.exe", server="server0185.articy.com", serverPort=13170, auth_file=None, articy_api_lib=r"C:\soft\articy_draft_API"):
    authStr = "" if auth_file == None else "--auth_file {auth_file}"
    #'start cmd "ARTICY POPULATOR" /k \"{ironPythonExePath}\" "{_POP_FILE_PATH}" {verbosityFlag} "{compilerOutputInputFile}" --project "{project}" --server {server} --server_port {serverPort} --project {project} {authStr}'
    runArgs = ["start", "cmd", "\"ARTICY POPULATOR\"", "/k", ironPythonExePath, _POP_FILE_PATH, verbosityFlag, compilerOutputInputFile, "--project", project, "--server", server, "--server_port", str(serverPort), "--project", project, "--articy_api_lib", articy_api_lib]
    if auth_file:
        runArgs.extend(["--auth_file", auth_file])
    print(runArgs)
    logger.info("Running cmd: {}".format(' '.join([str(e) for e in runArgs])))
    subprocess.run(runArgs, shell=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=argparse.RawDescriptionHelpFormatter)
    # parser.add_argument("-f", "--flag", action="store_true", help="Example argparse of a choice")
    # parser.add_argument("-c", "--choice", default="c1", choices=["c1", "c2", "c3", "c4"], help="Example of an argparse choice argument")
    # parser.add_argument("-o", "--optional", help="Example of an optional flag with an argument")
    parser.add_argument("intput_file", help="The input document file")
    parser.add_argument("-o", "--output", default="out.json", help="The output file path")
    parser.add_argument("--output_images", help="If set will save the images into this directory, else a directory will be created next to the output json")
    parser.add_argument("-r", "--raw", help="A slightly formated raw output of the document")
    parser.add_argument("--debug_dir", help="A debug directory into which to write debug files")
    
    k3logging.set_parser_log_arguments(parser)
    
    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
    
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
    
    ast, lines = doc_parser.parse(args.intput_file, imgOutputPath)
    
    if args.debug_dir:
        debugDirPath = os.path.abspath(args.debug_dir)
    
        try:
            os.makedirs(debugDirPath)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            
        rawOutputLocaiton = os.path.join(debugDirPath,"doc_output.raw")
        with open(rawOutputLocaiton, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        
        linesOutputLocaiton = os.path.join(debugDirPath,"doc_output.json")
        with open(linesOutputLocaiton, "w") as fh:
            json.dump(lines, fh, indent=2)
    
            logger.info(f"A copy was written to {linesOutputLocaiton}")
    
        lexOutPath = os.path.join(debugDirPath,"lexer_output.json")

        with open(lexOutPath, "w") as fh:
            json.dump(ast, fh, indent=2)
    
        logger.info(f"Parsed and structured (lexing) output written to {lexOutPath}")
    
    logger.info(f"Parsing and structuring the input (lexing) complete")
    
    if args.raw:
        with open(args.raw, "w", encoding="utf-8") as fh:
            for i, line in enumerate(lines):
                if i > 0:
                    fh.write("\n")
                if line.startswith("*"):
                    fh.write(line)
                elif line.startswith("§"):
                    fh.write("  " + line)
                else:
                    fh.write("    " + line)
        logger.info(f"Wrote text output of input to {args.raw}")
    
    resultJson = story_compiler.compile_story(ast)
    
    logger.info(f"Compilation complete")
    
    with open(outputPath, "w") as fh:
        json.dump(resultJson, fh, indent=2)
        
    logger.info(f"Final (compiled) output written to {outputPath}")
