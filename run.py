


from lw_doc_extractor.main import cli
import sys
import socket
from lw_doc_extractor import story_compiler
import json
import logging


    

def prog2():
    logging.basicConfig(level=logging.DEBUG)
    with open(r"C:\git\lw-doc-extractor\test_files\debug\lexer_output.json") as fh:
        ast = json.load(fh)
        story_compiler.compile_story(ast)

def prog1():
    print(socket.gethostname())
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        #sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\StoryGym.docx", "-o", "test_files\comp_output.json"] 
        #sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\StoryGymT.docx", "-o", "test_files\comp_output.json"] 
        #sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\ChapterLeviesFeast.docx", "-o", "test_files\comp_output.json"]
        sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\Levi's Feast - ArticyScript.docx", "-o", "test_files\comp_output.json"]
        
        
        
    cli.main()
    
if __name__ == '__main__':
    prog1()