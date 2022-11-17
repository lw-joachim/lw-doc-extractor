


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
    

def prog1r():
    print(socket.gethostname())
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", "C:\work\plastic_cloud\ONEof500-Game\One\Content\Story\LF\LF.docx", "-o", "C:\work\plastic_cloud\ONEof500-Game\One\Content\Story\LF\compiler_output.json", "-r", "C:\work\plastic_cloud\ONEof500-Game\One\Content\Story\LF\LF.txt", "--debug_dir", "test_files/debug"]
    cli.main()

def prog3r():
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", "C:\work\plastic_cloud\ONEof500-Game\One\Content\Story\LF\compiler_output.json", "--auth_file", "test_files\mycred", "--project", "OneArticy"]
    cli.run_populator_main()
    
def prog3t():
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", "C:\work\plastic_cloud\ONEof500-Game\One\Content\Story\LF\compiler_output.json", "--auth_file", "test_files\mycred"]
    cli.run_populator_main()
    
def prog5r():
    logging.basicConfig(level=logging.DEBUG)
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", "C:\work\plastic_cloud\ONEof500-Game\One\Content\Story\LF\compiler_output.json", "test_files\\real\\lines.json"]
        
    tools.extract_dialog_lines()
    
    with open("test_files\\real\\lines.json") as fh:
        al = json.load(fh)
    # "C:\work\plastic_cloud\ONEof500-Game\One\Content\Story\LF\\audio_out"
    tools.generate_audio_files(al, "audio_out", "test_files\\tts_key.json")
    
    
if __name__ == '__main__':
    prog1r()
    #prog3r()
    #prog5r()
