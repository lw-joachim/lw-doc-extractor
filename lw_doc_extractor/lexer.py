'''
Created on 8 Jul 2022

@author: joachim
'''



import lark
import os
import logging

logger = logging.getLogger(__name__)

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

class StatementTransformer(lark.Transformer):
    def simple_dialog_statement(self, items):
        return "DIALOG_LINE", items[0].value, items[1].value
    
    def jump_statement(self, items):
        return items[0].type, items[1].value
    
    def player_choice(self, items):
        returnDict = {}
        for item in items:
            if type(item) == lark.Token:
                if item.type == "MENU_TEXT":
                    returnDict["menu_text"] = item.value
                elif item.type == "SPOKEN_TEXT":
                    returnDict["spoken_text"] = item.value
                else:
                    #logger.warning("Unexpected token in ")
                    raise RuntimeError(f"Unexpected token {item.type} in player_choice")
            elif type(item) == lark.Tree:
                if item.data == "conditional":
                    returnDict["condition"] = item.children[0].value
                elif item.data == "exit_instruction":
                    returnDict["exit_instruction"] = item.children[0].value
                elif item.data == "inner_sequence":
                    returnDict["sequence"] = item.children
                else:
                    raise RuntimeError(f"Unexpected tree {item.data} in player_choice")
        return returnDict
    
    def player_choice_block(self, items):
        # items are already a list of choices
        return items
    
    def choice_dialog_statement(self, items):
        return "CHOICE_DIALOG", {"entity" : items[0].value, "choices" : items[1:]}

class SequenceTransformer(lark.Transformer):
    
    def referenced_sequence(self, items):
        pass

class NodeDefinitionTransformer(lark.Transformer):
    
    def node_definition(self, items):
        pass
    
    def node_type(self, items):
        pass

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
    tree = lark.Lark(fileCont, start='start', parser='earley', debug=True).parse(cont)
    
    print_rec(tree)
    
    for c in tree.children:
        if type(c) == lark.Token:
            pass
        else:
            if c.data == "node_definition":
                for cc in c.children:
                    if type(cc) == lark.Token and cc.type == "ID" and cc.value =="A-Market_Zealot-Dialog":
                        print_rec(c)
                        
                        print("================")
                        n = StatementTransformer().transform(c)
                        #n = SequenceTransformer().transform(n)
                        print("================")
                        
                        print_rec(n)
                        return
    
    
    
    
def print_rec(tree, prefix=""):
    if type(tree) == lark.Tree:
        print(prefix+tree.data)
        for d in tree.children:
            print_rec(d, prefix+" ")
    elif type(tree) == lark.Token:
        print("{}token: {} = \t{}".format(prefix, tree.type, tree.value))
    else:
        print("{}{}".format(prefix, tree))
    
    #print(ret.pretty())