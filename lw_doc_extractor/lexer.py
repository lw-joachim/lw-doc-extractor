'''
Created on 8 Jul 2022

@author: joachim
'''



import lark
import os
import logging
import collections
import json

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
    
    def start_quest(self, items):
        return "START_QUEST", items[0].value
    
    def end_quest(self, items):
        return "END_QUEST", items[0].value
    
    def node_ref_statement(self, items):
        condition = None
        instruction = None
        for item in items:
            if type(item) == lark.Tree:
                if item.data == "conditional":
                    condition = item.children[0].value
                elif item.data == "exit_instruction":
                    instruction = item.children[0].value
        return "NODE_REF", items[0].value, condition, instruction
    
    def load_stage_statement(self, items):
        return "LOAD_STAGE", items[0].value
    
    def sync_game_event_statement(self, items):
        return "SYNC_GAME_EVENT", items[0].value
    
    def game_event_statement(self, items):
        return "GAME_EVENT", items[0].value
    
    def hub_choice(self, items):
        returnDict = {"choice_description" : None, "condition" : None, "exit_instruction": None, "sequence" : None}
        for item in items:
            if type(item) == lark.Token:
                if item.type == "REST_OF_LINE_TEXT":
                    returnDict["choice_description"] = item.value
                else:
                    raise RuntimeError(f"Unexpected token {item.type} in hub_choice")
            elif type(item) == lark.Tree:
                if item.data == "conditional":
                    returnDict["condition"] = item.children[0].value
                elif item.data == "exit_instruction":
                    returnDict["exit_instruction"] = item.children[0].value
                elif item.data == "inner_sequence":
                    returnDict["sequence"] = item.children
                else:
                    raise RuntimeError(f"Unexpected tree {item.data} in hub_choice")
            else:
                raise RuntimeError(f"Unexpected type in hub_choice {item}")
        return returnDict
    #
    def hub_statement_block(self, items):
        return "HUB", items
    
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
            else:
                raise RuntimeError(f"Unexpected type in player_choice {item}")
        return returnDict
    
    def player_choice_block(self, items):
        # items are already a list of choices
        return items
    
    def choice_dialog_statement(self, items):
        return "CHOICE_DIALOG", {"entity" : items[0].value, "choices" : items[1]}
    
    def sequence(self, items):
        return items
    
    def if_block(self, items):
        ret =  "IF", {"eval_condition" : items[0].value, "sequence_true":items[1].children, "sequence_false": items[2].children}
        return ret

class DocTransformer(lark.Transformer):
    
    def start(self, items):
        return {"chapter_node" : items[0], "nodes" : items[1:]}
    
    def start_node(self, items):
        rd = self.node_definition(items)
        rd["node_type"] = "Chapter"
        return rd
    
    def _p_node_properties(self, node_prop, nodeDict):
        for item in node_prop.children:
            if item.data == "description":
                nodeDict["description"] = item.children[0].value
            if item.data == "image":
                nodeDict["image"] =item.children[0].value

    def node_definition(self, items):
        nodeDict = {"id" : None, "node_type" : None, "description": None, "image" : None, "start_sequence" : None, "referenced_sequences": collections.OrderedDict()}
        for item in items:
            # print("=============")
            # print(type(item))
            if type(item) == lark.Token:
                if item.type == "ID":
                    nodeDict["id"] = item.value
                else:
                    raise RuntimeError(f"Unexpected token {item.type} in node_definition")
            elif type(item) == lark.Tree:
                if item.data == "node_type":
                    nodeDict["node_type"] = item.children[0].value
                elif item.data == "start_sequence":
                    nodeDict["start_sequence"] = item.children[0]
                elif item.data == "referenced_sequence":
                    nodeDict["referenced_sequences"][item.children[0].value] = item.children[1]
                elif item.data == "node_properties":
                    self._p_node_properties(item, nodeDict)
                else:
                    raise RuntimeError(f"Unexpected tree {item.data} in node_definition")
            else:
                raise RuntimeError(f"Unexpected type in node_definition {item}")
        print(nodeDict["id"])
        return nodeDict

def parse(lines):
    cont = "\n".join(lines)
    
    with open(os.path.join(_FILE_LOC, "grammar_defn"), "r") as f:
        fileCont = f.read()
    
    print("======================")
    tree = lark.Lark(fileCont, start='start', parser='earley', debug=True).parse(cont)
    
    #print_rec(tree)
    
    # for c in tree.children:
    #     if type(c) == lark.Token:
    #         pass
    #     else:
    #         if c.data == "node_definition":
    #             for cc in c.children:
    #                 if type(cc) == lark.Token and cc.type == "ID" and cc.value =="A-Market_Zealot-Dialog":
    #                     print_rec(c)
    #
    #                     print("================")
    #                     n = StatementTransformer().transform(c)
    #                     #n = SequenceTransformer().transform(n)
    #                     n = NodeDefinitionTransformer().transform(n)
    #                     print("================")
    #
    #                     print_rec(n)
    #                     return
    
    n = StatementTransformer().transform(tree)
    n = DocTransformer().transform(n)
    
    # print("=======\nChapter node:")
    # print_node("", n["chapter_node"])
    # print("=======\nNodes")
    # for restNode in n["nodes"]:
    #     print_node("", restNode)
        
    logger.info("Lexing complete")

    return n
    
def pp(prefix, txt):
    print(prefix+str(txt))
    
def pp_dict(prefix, d, exclKeys=[]):
    dcpy = dict(d)
    for k in exclKeys:
        dcpy.pop(k)
    print(prefix+str(dcpy))
    
def p_inner_seq(prefix, seq):
    for st in seq:
        if type(st) == lark.Tree:
            pp(prefix, st)
        elif st[0] == "CHOICE_DIALOG":
            pp(prefix, "CHOICE_DIALOG")
            for choice in st[1]["choices"]:
                pp_dict(prefix+"  ", choice, ["sequence"])
                for s in choice["sequence"]:
                    pp(prefix+"    ", s)
        elif st[0] == "HUB":
            pp(prefix, "HUB")
            for choice in st[1]:
                pp_dict(prefix+"  ", choice, ["sequence"])
                for s in choice["sequence"]:
                    pp(prefix+"    ", s)
        else:  
            pp(prefix, st)

def print_node(prefix, nodeDict):
    pp(prefix, "*"+nodeDict["id"] +"(" +nodeDict["node_type"]+ ")")
    prefix+="  "
    pp(prefix , "node_properties : " + str(nodeDict["node_properties"] ))
    pp(prefix, "start_sequence")
    p_inner_seq(prefix+"  ", nodeDict["start_sequence"])
    for k, v in nodeDict["referenced_sequences"].items():
        pp(prefix, "referenced_sequences "+k)
        p_inner_seq(prefix+"  ", v)
    
    

def print_dict_rec(prefix, d):
    if type(d) == dict:
        for k, v in d.items():
            print(prefix+k)
            print_dict_rec()
            
    
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