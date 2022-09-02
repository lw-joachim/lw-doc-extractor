


from lw_doc_extractor.main import cli
import sys
import socket

if __name__ == '__main__':
    
    print(socket.gethostname())
    if "shoebill" == socket.gethostname():
        old_sys_argv = sys.argv
        #sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\StoryGym.docx", "-o", "test_files\comp_output.json"] 
        sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\StoryGymT.docx", "-o", "test_files\comp_output.json"] 
        #sys.argv = [old_sys_argv[0]] + ["-vv", "test_files\ChapterLeviesFeast.docx", "-o", "test_files\comp_output.json"]
        
        
    cli.main()