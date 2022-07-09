'''
Created on 8 Jul 2022

@author: joachim
'''



from lark import Lark
import os

_FILE_LOC = os.path.abspath(os.path.dirname(__file__))

# LARK_PARSER = Lark(r"""
#
# script : node_definition | _NEWLINE
#
# node_definition  : _node_marker node_type id LINES+
#
#
# node_type : node_type_dialog | "Section" | "Chapter"
#
# node_type_dialog : "[D-DEF]" | "[D-EAV]"
#
# _node_marker : _NEWLINE "*"
#
# LINES : _NEWLINE | ([^\*].* _NEWLINE)
#
# COMMENT: /#[^\n]*/
# _NEWLINE: ( /\r?\n[\t ]*/ | COMMENT )+
#
# %ignore /[\t \f]+/  // WS
# %ignore COMMENT
#
# """, start='script', parser='earley')



def parse(lines):
    for i, l in enumerate(lines):
        print(f"{l}")
        
        
    for i, l in enumerate(lines):
        print(f"{i:<3} {l}")
        
        
    cont = "\n".join(lines)
    
    with open(os.path.join(_FILE_LOC, "grammar_defn"), "r") as f:
        fileCont = f.read()
    
    print(fileCont)
    print("======================")
    ret = Lark(fileCont, start='start', parser='earley', debug=True).parse(cont)
    print(ret.pretty())