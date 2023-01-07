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
from multiprocessing.connection import Listener, Connection
import socket

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
        
    run_populator(args.input_file, args.project, verboseFlag, args.iron_python, args.server,args.server_port, args.auth_file, args.articy_api_lib )
    

def run_populator(compilerOutputInputFile, project="api_test_proj", verbosityFlag="-v", ironPythonExePath=r"C:\Program Files\IronPython 2.7\ipy.exe", server="server0185.articy.com", serverPort=13170, auth_file=None, articy_api_lib=r"C:\soft\articy_draft_API"):
    authStr = "" if auth_file == None else "--auth_file {auth_file}"
    #'start cmd "ARTICY POPULATOR" /k \"{ironPythonExePath}\" "{_POP_FILE_PATH}" {verbosityFlag} "{compilerOutputInputFile}" --project "{project}" --server {server} --server_port {serverPort} --project {project} {authStr}'
    runArgs = ["start", "cmd", "\"ARTICY POPULATOR\"", "/k", ironPythonExePath, _POP_FILE_PATH, verbosityFlag, compilerOutputInputFile, "--project", project, "--server", server, "--server_port", str(serverPort), "--project", project, "--articy_api_lib", articy_api_lib, "--callback_srv_on_complete", "127.0.0.1:31431"]
    if auth_file:
        runArgs.extend(["--auth_file", auth_file])
    print(runArgs)
    logger.info("Running cmd: {}".format(' '.join([str(e) for e in runArgs])))
    subprocess.run(runArgs, shell=True)
    
    logger.info("Waiting for populator to be complete")
    
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 31431))
        s.settimeout(240)
        s.listen()
        conn, addr = s.accept()
        resBytes = b''
        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                resBytes = resBytes + data
        jsonStr = resBytes.decode("utf-8")
        logger.info(f"Message received from populator: {jsonStr}")
        respObj = json.loads(jsonStr)
        if respObj["exit_state"] != "ok":
            raise RuntimeError(f"Populator exited early with error message: {respObj['error_message']}")

    
    # with Listener(("127.0.0.1", 31431), authkey=b'sajkfkhj') as listener:
    #     with listener.accept() as conn:
    #         rbytes = conn.recv_bytes()
    #         jsonStr = rbytes.decode("utf-8")
    #         logger.info(f"Message received from populator: {jsonStr}")
    #         respObj = json.loads(jsonStr)
    #         if respObj["exit_state"] != "OK":
    #             raise RuntimeError(f"Populator exited early with error message: {respObj['error_message']}")
            
    logger.info(f"Populating articy project {project} complete")


def run_main(sriptInputFile, outputPath, rawOutputPath=None, imgOutputPath=None, debugDirPath=None):
    if imgOutputPath:
        try:
            os.makedirs(os.path.dirname(imgOutputPath))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            
    outputDirPath = os.path.dirname(outputPath)
    
    ast, lines = doc_parser.parse(sriptInputFile, imgOutputPath)
    
    if debugDirPath:
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
    
    if rawOutputPath:
        with open(rawOutputPath, "w", encoding="utf-8") as fh:
            for i, line in enumerate(lines):
                if i > 0:
                    fh.write("\n")
                if line.startswith("*"):
                    fh.write(line)
                elif line.startswith("§"):
                    fh.write("  " + line)
                else:
                    fh.write("    " + line)
        logger.info(f"Wrote raw text output of input to {rawOutputPath}")
    
    resultJson = story_compiler.compile_story(ast)
    
    logger.info(f"Compilation complete")
    
    with open(outputPath, "w") as fh:
        json.dump(resultJson, fh, indent=2)
        
    logger.info(f"Final (compiled) output written to {outputPath}")
    

def main():
    parser = argparse.ArgumentParser(description=__doc__+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_file", help="The input document file")
    parser.add_argument("-o", "--output", default="out.json", help="The output file path")
    parser.add_argument("--output_images", help="If set will save the images into this directory, else a directory will be created next to the output json")
    parser.add_argument("-r", "--raw", help="A slightly formated raw output of the document")
    parser.add_argument("--debug_dir", help="A debug directory into which to write debug files")
    
    k3logging.set_parser_log_arguments(parser)
    
    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
    
    run_main(args.input_file, args.output, args.raw, None, args.debug_dir)

