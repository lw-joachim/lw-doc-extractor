from lw_doc_extractor.main import cli, tools
import sys
import socket
from lw_doc_extractor import story_compiler
import json
import logging
import shutil
import os


def prog4():
    logging.basicConfig(level=logging.DEBUG)
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", r"test_files\manual\comp_output.json", r"test_files\lines.json"]
        
    tools.extract_dialog_lines_cli()
    
    with open("test_files\lines.json") as fh:
        al = json.load(fh)
    tools.update_audio_files(al, r"test_files\audio_out", "test_files\\oo5_key.json")


def compile_file_manual(inpFile):
    #print(socket.gethostname())
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        shutil.rmtree(r"test_files\manual", ignore_errors=True)
        #sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\StoryGym.docx", "-o", "test_files\comp_output.json"] 
        #sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\StoryGymT.docx", "-o", "test_files\comp_output.json"] 
        #sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\ChapterLeviesFeast.docx", "-o", "test_files\comp_output.json"]
        sys.argv = [old_sys_argv[0]] + ["-v", inpFile, "-o", r"test_files\manual\comp_output.json",  "--debug_dir", r"test_files\manual"]
    cli.main()
    
def prog2():
    logging.basicConfig(level=logging.DEBUG)
    with open(r"test_files\manual\lexer_output.json") as fh:
        ast = json.load(fh)
        resultJson = story_compiler.compile_story(ast)
        with open(r"test_files\manual\comp_output.json", "w") as fh:
            json.dump(resultJson, fh, indent=2)

def prog3():
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-vv", r"test_files\manual\comp_output.json", "--auth_file", "test_files\mycred"]
    cli.run_populator_main()

def prog1r():
    print(socket.gethostname())
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", r"C:\work\plastic_cloud\ONEof500-Game\One\Story\Chapters\LF\Script\LF.docx", "-o", r"C:\work\plastic_cloud\ONEof500-Game\One\Story\Chapters\LF\GeneratedFiles\compiler_output.json", "-r", r"C:\work\plastic_cloud\ONEof500-Game\One\Story\Chapters\LF\Script\LF_raw.txt", "--debug_dir", "test_files/debug"]
    cli.main()
    
def prog1t():
    print(socket.gethostname())
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", r"C:\work\plastic_cloud\ONEof500-Game\One\Story\Chapters\LF\Script\LF.docx", "-o", "test_files/compiler_output.json", "-r", "test_files/LF_raw.txt", "--debug_dir", "test_files/debug"]
    cli.main()

def prog3r():
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", r"C:\work\plastic_cloud\ONEof500-Game\One\Story\Chapters\LF\GeneratedFiles\compiler_output.json", "--auth_file", "test_files\mycred", "--project", "OneArticy", "--target_flow_fragment", "One"]
    cli.run_populator_main()
    
def prog3t():
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", r"C:\work\plastic_cloud\ONEof500-Game\One\Story\Chapters\LF\GeneratedFiles\compiler_output.json", "--auth_file", "test_files\mycred", "--target_flow_fragment", "One"]
    cli.run_populator_main()
    
def prog5r():
    logging.basicConfig(level=logging.DEBUG)
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", r"C:\work\plastic_cloud\ONEof500-Game\One\Story\Chapters\LF\GeneratedFiles\compiler_output.json", "test_files\\real\\lines.json"]
        
    tools.extract_dialog_lines_cli()
    
    with open("test_files\\real\\lines.json") as fh:
        al = json.load(fh)
    # "C:\work\plastic_cloud\ONEof500-Game\One\Story\LF\\audio_out"
    tools.update_audio_files(al, "test_files\\audio_out", "test_files\\oo5_key.json")
    
def prog6r():
    logging.basicConfig(level=logging.DEBUG)
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", r"C:\work\plastic_cloud\ONEof500-Game\One\Story\LF\compiler_output.json", "test_files\\script_out"]
    
    
    tools.generate_audio_recording_files_cli()
    
def prog_update_story_dry_run(chapterDoc):
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        shutil.rmtree("test_files\\dry_run_dir")
        sys.argv = [old_sys_argv[0]] + ["-v", chapterDoc, "C:\work\plastic_cloud\ONEof500-Game\One", "--gauth", "test_files\\oo5_key.json", "--articy-config", "test_files\\articy_config.json", "--dry-run", "--dry-run-dir", "test_files\\dry_run_dir", "--dry-run-audio"]
    try:
        tools.update_story_chapter_cli()
    finally:
        print("Done")
        
def prog_update_story(docxFilePath, dry_run=True):
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        if dry_run:
            if os.path.exists("test_files\\dry_run_dir"):
                shutil.rmtree("test_files\\dry_run_dir")
        sys.argv = [old_sys_argv[0]] + ["-v", docxFilePath, "C:\work\plastic_cloud\ONEof500-Game\One", "--gauth", "test_files\\oo5_key.json", "--articy-config", "test_files\\articy_config.json"] + ([] if not dry_run else ["--dry-run", "--dry-run-dir", "test_files\\dry_run_dir", "--dry-run-audio"])
    try:
        tools.update_story_chapter_cli()
    finally:
        print("Done")
        
def prog_update_story_lf():
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", "test_files\\LF.docx", "C:\work\plastic_cloud\ONEof500-Game\One", "--gauth", "test_files\\oo5_key.json", "--articy-config", "test_files\\articy_config.json"]#, "--dry-run-audio"]
    try:
        tools.update_story_chapter_cli()
    finally:
        print("Done")
        
def export_audio_bank():
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        shutil.rmtree(r"test_files\audio_exp")
        os.mkdir(r"test_files\audio_exp")
        #shutil.rmtree(r"test_files\audio_exp\audio")
        os.mkdir(r"test_files\audio_exp\audio")
        sys.argv = [old_sys_argv[0]] + ["-vv", "C:\work\plastic_cloud\ONEof500-Game\One", "-r", r"test_files\audio_exp", "-a", r"test_files\audio_exp\audio"]
    tools.audio_bank_for_complete_project_cli()
        
def sort_audio_bank_emotion():
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        shutil.rmtree(r"test_files\audio_exp\sorted", ignore_errors=True)
        os.mkdir(r"test_files\audio_exp\sorted")
        sys.argv = [old_sys_argv[0]] + ["-v", r"C:\work\plastic_cloud\ONEof500-Game\One\Story\Chapters\LF\GeneratedFiles\compiler_output.json", r"test_files\audio_exp\audio", r"test_files\audio_exp\sorted"]
    tools.sort_audio_files_by_emotion_cli()

    
def prog8t():
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        sys.argv = [old_sys_argv[0]] + ["-v", r"C:\work\plastic_cloud\ONEof500-Game\One\Story\Chapters\LF\GeneratedFiles\compiler_output.json", r"test_files\audio_out", r"test_files\audio_out_sorted", ]
    tools.sort_audio_files_by_emotion_cli()
    
    
if __name__ == '__main__':
    #compile_file_manual(r"C:\Users\joachim\Documents\OneOf500ChapterScripts\GYH.docx")
    #compile_file_manual(r"C:\work\plastic_cloud\ONEof500-Game\One\Story\Chapters\ORA\Script\ORA.docx")
    #compile_file_manual(r"C:\work\plastic_cloud\ONEof500-Game\One\Story\Chapters\LF\Script\LF.docx")
    
    prog_update_story(r"C:\Users\joachim\Documents\OneOf500ChapterScripts\GYH.docx", dry_run=True)
    #prog3()
    #prog1t()
    #prog3r()
    #prog6r()
    #prog7t()
    
    #prog3t()
    #prog8t()
    #prog_update_story_dry_run(asdf)
    #prog_update_story()
    #export_audio_bank()
    #sort_audio_bank_emotion()
    
