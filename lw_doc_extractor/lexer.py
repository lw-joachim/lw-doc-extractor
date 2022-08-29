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

    def _process_generic_statement_args(self, items, includesCondInst=False, hasDescription=False, defVals={}):
        resp = {}
        resp.update(defVals)
        if hasDescription:
            resp["description"] = None
        if includesCondInst:
            resp["condition"] = None
            resp["exit_instruction"] = None
        for item in items:
            if type(item) == lark.Token:
                if item.type == "STATEMENT_DESCRIPTION":
                    resp["description"] = item.value.strip()
                else:
                    resp[item.type.lower()] = item.value.strip()
            elif type(item) == lark.Tree:
                if item.data == "condition":
                    resp['condition'] = item.children[0].value.strip()
                elif item.data == "exit_instruction":
                    resp['exit_instruction'] = item.children[0].value.strip()
        return resp
        
    def simple_dialog_statement(self, items):
        #return "DIALOG_LINE", items[0].value, items[1].value
        return "DIALOG_LINE" , self._process_generic_statement_args(items, includesCondInst=True, defVals={"menu_text":None, "stage_directions" : None})
    
    def internal_jump_statement(self, items):
        return "INTERNAL_JUMP", self._process_generic_statement_args(items)
    
    def external_jump_statement(self, items):
        return "EXTERNAL_JUMP", self._process_generic_statement_args(items)
    
    def start_quest_statement(self, items):
        return "START_QUEST", self._process_generic_statement_args(items)
    
    def end_quest_statement(self, items):
        return "END_QUEST", self._process_generic_statement_args(items)
    
    def load_stage_statement(self, items):
        return "LOAD_STAGE", self._process_generic_statement_args(items, hasDescription=True)
    
    def sync_stage_event_statement(self, items):
        return "SYNC_STAGE_EVENT", self._process_generic_statement_args(items, hasDescription=True)
    
    def stage_event_statement(self, items):
        return "STAGE_EVENT", self._process_generic_statement_args(items, hasDescription=True)
    
    def set_statement(self, items):
        return "SET", self._process_generic_statement_args(items) 
    
    def game_event_listener_statement(self, items):
        return "GAME_EVENT_LISTENER", self._process_generic_statement_args(items, hasDescription=True)
    
    def the_end_statement(self, items):
        return "THE_END", self._process_generic_statement_args(items, hasDescription=True)
    
    
    def node_ref_statement(self, items):
        return "NODE_REF", self._process_generic_statement_args(items)
    
    # def _process_generic_statement(self, name, *args, **kwargs):
    #     items = args[0]
    #     statement = name[:-len("_statement")]
    #     resp = {}
    #     for item in items:
    #         if type(item) == lark.Token:
    #             resp[item.type.lower()] = item.value
    #         elif type(item) == lark.Tree:
    #             if item.data == "condition":
    #                 resp['condition'] = item.children[0].value
    #             elif item.data == "exit_instruction":
    #                 resp['instruction'] = item.children[0].value
    #     return statement.upper(), resp
    #
    # def __getattr__(self, name):
    #     print(name)
    #     if name.lower().endswith("_statement"):
    #         def method(*args, **kwargs):
    #             return self._process_generic_statement(name, *args, **kwargs)
    #     raise AttributeError(f"Name {name} not part of {type(self)}")
    
    def hub_choice(self, items):
        returnDict = {"choice_description" : None, "condition" : None, "exit_instruction": None, "sequence" : None, "event_id" : None}
        for item in items:
            if type(item) == lark.Token:
                if item.type == "STATEMENT_DESCRIPTION":
                    returnDict["choice_description"] = item.value.strip()
                elif item.type == "EVENT_ID":
                    returnDict["event_id"] = item.value.strip()
                else:
                    raise RuntimeError(f"Unexpected token {item.type} in hub_choice")
            elif type(item) == lark.Tree:
                if item.data == "condition":
                    returnDict["condition"] = item.children[0].value.strip()
                elif item.data == "exit_instruction":
                    returnDict["exit_instruction"] = item.children[0].value.strip()
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
        returnDict = {"menu_text" : None, "spoken_text" : None, "stage_directions" : None, "condition" : None, "exit_instruction": None, "sequence" : None}
        for item in items:
            if type(item) == lark.Token:
                if item.type == "MENU_TEXT":
                    returnDict["menu_text"] = item.value.strip()
                elif item.type == "SPOKEN_TEXT":
                    returnDict["spoken_text"] = item.value.strip()
                else:
                    #logger.warning("Unexpected token in ")
                    raise RuntimeError(f"Unexpected token {item.type} in player_choice")
            elif type(item) == lark.Tree:
                if item.data == "condition":
                    returnDict["condition"] = item.children[0].value.strip()
                elif item.data == "exit_instruction":
                    returnDict["exit_instruction"] = item.children[0].value.strip()
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
        return "CHOICE_DIALOG", {"entity_name" : items[0].value, "choices" : items[1]}
    
    def sequence(self, items):
        filteredItems = [item for item in items if type(item) == lark.Tree or  type(item) == lark.Token]
        if len(filteredItems) > 0:
            logger.warning(f"In sequence filtered the following: {filteredItems}")
        return [item for item in items if type(item) != lark.Tree or  type(item) != lark.Token]
    
    def if_block(self, items):
        ret =  "IF", {"eval_condition" : items[0].value.strip(), "sequence_true":items[1].children, "sequence_false": items[2].children}
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
            if item.data == "node_description":
                nodeDict["description"] = item.children[0].value.strip()
            if item.data == "image":
                nodeDict["image"] =item.children[0].value

    def node_definition(self, items):
        nodeDict = {"id" : None, "node_type" : None, "description": None, "image" : None, "start_sequence" : None, "referenced_sequences": collections.OrderedDict()}
        for item in items:
            # print("=============")
            # print(type(item))
            if type(item) == lark.Token:
                if item.type == "ID":
                    nodeDict["id"] = item.value.strip()
                else:
                    raise RuntimeError(f"Unexpected token {item.type} in node_definition")
            elif type(item) == lark.Tree:
                if item.data == "node_type":
                    nodeDict["node_type"] = item.children[0].value.strip()
                elif item.data == "start_sequence":
                    nodeDict["start_sequence"] = item.children[0]
                elif item.data == "referenced_sequence":
                    nodeDict["referenced_sequences"][item.children[0].value.strip()] = item.children[1]
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
    
    tree = lark.Lark(fileCont, start='start', parser='earley').parse(cont)
    
    n = StatementTransformer().transform(tree)
    n = DocTransformer().transform(n)
    
    # print("=======\nChapter node:")
    # print_node("", n["chapter_node"])
    # print("=======\nNodes")
    # for restNode in n["nodes"]:
    #     print_node("", restNode)

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
    pp(prefix , "description : " + str(nodeDict["description"] ))
    pp(prefix , "image : " + str(nodeDict["image"] ))
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