


from lw_doc_extractor.main import cli, tools
import sys
import socket
from lw_doc_extractor import story_compiler
import json
import logging


def prog4():
    logging.basicConfig(level=logging.DEBUG)
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\comp_output.json", "test_files\lines.json"]
        
    tools.extract_dialog_lines()
    
    with open("test_files\lines.json") as fh:
        al = json.load(fh)
    tools.generate_audio_files(al, "audio_out", "test_files\\tts_key.json")
    

def prog2():
    logging.basicConfig(level=logging.DEBUG)
    with open(r"C:\git\lw-doc-extractor\test_files\debug\lexer_output.json") as fh:
        ast = json.load(fh)
        story_compiler.compile_story(ast)
        
def prog3():
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\comp_output.json", "--auth_file", "test_files\mycred", "--project", "OneArticy"]
    cli.run_populator_main()
    
def prog31():
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\comp_output.json", "--auth_file", "test_files\mycred"]
    cli.run_populator_main()

def prog1():
    print(socket.gethostname())
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        #sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\StoryGym.docx", "-o", "test_files\comp_output.json"] 
        #sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\StoryGymT.docx", "-o", "test_files\comp_output.json"] 
        #sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\ChapterLeviesFeast.docx", "-o", "test_files\comp_output.json"]
        sys.argv = [old_sys_argv[0]] + ["-v", "test_files\Levi's Feast - ArticyScript.docx", "-o", "test_files\comp_output.json"]
    cli.main()
    
if __name__ == '__main__':
    prog1()
    prog3()