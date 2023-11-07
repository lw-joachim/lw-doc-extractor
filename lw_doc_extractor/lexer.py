# -*- coding: utf-8 -*-
'''
Created on 8 Jul 2022

@author: joachim
'''



import lark
import os
import logging
import collections
import json
from lark.exceptions import LarkError, UnexpectedInput
import traceback

logger = logging.getLogger(__name__)

_FILE_LOC = os.path.abspath(os.path.dirname(__file__))

_GRAMMAR_FOLDER = os.path.join(_FILE_LOC, "grammar_definitions")

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

def _fix_cond_instr_str(thestring):
    return thestring.strip().replace("“", '"').replace("”", '"')

class StatementTransformer(lark.Transformer):
    
    VALID_LINE_EMOTIONS = ["neutral", "angry", "annoyed", "disgusted", "afraid", "happy", "sad", "surprised", "thoughtful", "amazed", "determined"]

    def _convert_lark_to_json(self, item):
        if type(item) == lark.Token:
            tokenNm = item.type.lower()
            if tokenNm.startswith("__anon"):
                return item.value.strip()
            return {item.type.lower() : item.value.strip()}
        if type(item) == lark.Tree:
            return {item.data.lower() : [(None if citem is None else self._convert_lark_to_json(citem)) for citem in item.children]}
        else:
            return item

    def _process_generic_statement_args(self, items, includesCondInst=False, hasDescription=False, defVals={}, transMap={}):
        resp = {}
        resp.update(defVals)
        if hasDescription:
            resp["description"] = None
        if includesCondInst:
            resp["condition"] = None
            resp["exit_instruction"] = None
        for item in items:
            if type(item) == lark.Token:
                for orgNm, tarNm in transMap.items():
                    if item.type == orgNm:
                        resp[tarNm] = item.value.strip()
                if item.type == "STATEMENT_DESCRIPTION":
                    resp["description"] = item.value.strip()
                elif item.type == "ENTITY_NAME":
                    resp["entity_name"] = item.value.strip().replace(" ", "_")
                elif item.type == "EVENT_ID":
                    resp["event_id"] = item.value.strip().replace(" ", "_")
                elif item.type == "INSTRUCTION":
                    resp['instruction'] = _fix_cond_instr_str(item.value)
                else:
                    resp[item.type.lower()] = item.value.strip()
            elif type(item) == lark.Tree:
                if item.data == "condition":
                    resp['condition'] = _fix_cond_instr_str(item.children[0].value)
                elif item.data == "exit_instruction":
                    resp['exit_instruction'] = _fix_cond_instr_str(item.children[0].value)
                else:
                    resp.update(self._convert_lark_to_json(item))
            elif type(item) == dict:
                resp.update(item)
            else:
                raise RuntimeError("Unprocessable item: "+str(item))
        return resp
    
    def line_attribute(self, items):
        return {items[0].children[0].value: items[0].children[1].value}
    
    def line_attributes(self, listOfLineAttrDict):
        usedKeys = []
        lineAttributes = {}
        for lineAttrDict in listOfLineAttrDict:
            for lineAttrKey, lineAttrVal in lineAttrDict.items():
                if lineAttrKey in usedKeys:
                    raise RuntimeError(f"Duplicate attribute '{lineAttrKey}'")
                usedKeys.append(lineAttrKey)
                
                if lineAttrKey == "emotion" and lineAttrVal not in StatementTransformer.VALID_LINE_EMOTIONS:
                    raise RuntimeError(f"Invalid attribute value '{lineAttrVal}' for attribute '{lineAttrKey}'")
                lineAttributes[lineAttrKey] = lineAttrVal
        return {"line_attributes" : lineAttributes }
        
    def simple_dialog_line(self, items):
        #return "DIALOG_LINE", items[0].value, items[1].value
        ret = "DIALOG_LINE" , self._process_generic_statement_args(items, includesCondInst=True, defVals={"menu_text":None, "stage_directions" : None, "line_attributes" : {}})
        if ret[1]["stage_directions"]:
            ret[1]["stage_directions"] = ret[1]["stage_directions"].strip("()").strip()
        return ret
    
    def internal_jump_statement(self, items):
        return "INTERNAL_JUMP", self._process_generic_statement_args(items)
    
    def external_jump_statement(self, items):
        return "EXTERNAL_JUMP", self._process_generic_statement_args(items)
    
    def start_quest_statement(self, items):
        return "START_QUEST", self._process_generic_statement_args(items, defVals={"quest_targets": []})
    
    def activate_quest_target_statement(self, items):
        return "ACTIVATE_QUEST_TARGET", self._process_generic_statement_args(items)
    
    def deactivate_quest_target_statement(self, items):
        return "DEACTIVATE_QUEST_TARGET", self._process_generic_statement_args(items)
    
    def end_quest_statement(self, items):
        return "END_QUEST", self._process_generic_statement_args(items)
    
    def load_stage_statement(self, items):
        return "LOAD_STAGE", self._process_generic_statement_args(items, hasDescription=True)
    
    def load_scenario_statement(self, items):
        return "LOAD_SCENARIO", self._process_generic_statement_args(items, hasDescription=True)
    
    def sync_stage_event_statement(self, items):
        return "SYNC_STAGE_EVENT", self._process_generic_statement_args(items, hasDescription=True)
    
    def stage_event_statement(self, items):
        return "STAGE_EVENT", self._process_generic_statement_args(items, hasDescription=True)
    
    def save_game_statement(self, items):
        return "SAVE_GAME", self._process_generic_statement_args(items, hasDescription=True, transMap={"SAVE_GAME_ID":"title"})
    
    def set_statement(self, items):
        return "SET", self._process_generic_statement_args(items)
    
    def game_event_listener_statement(self, items):
        return "GAME_EVENT_LISTENER", self._process_generic_statement_args(items, hasDescription=True)
    
    def the_end_statement(self, items):
        return "THE_END", self._process_generic_statement_args(items, hasDescription=True)
    
    def node_ref_statement(self, items):
        return "NODE_REF", self._process_generic_statement_args(items)
    
    def comment_statement(self, items):
        return "COMMENT", self._process_generic_statement_args(items, hasDescription=True, transMap={"COMMENT_TEXT":"description"})
    
    
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
    def shac_choice(self, items):
        returnDict = {"choice_description" : None, "sequence" : None, "event_id" : None}
        for item in items:
            if type(item) == lark.Token:
                if item.type == "STATEMENT_DESCRIPTION":
                    returnDict["choice_description"] = item.value.strip()
                elif item.type == "EVENT_ID":
                    returnDict["event_id"] = item.value.strip().replace(" ", "_")
                elif item.type == "CHOICE_INFINITE":
                    continue
                else:
                    raise RuntimeError(f"Unexpected token {item.type} in shac_choice")
            elif type(item) == lark.Tree:
                if item.data == "inner_sequence":
                    returnDict["sequence"] = item.children
                else:
                    raise RuntimeError(f"Unexpected tree {item.data} in shac_choice")
            else:
                raise RuntimeError(f"Unexpected type in shac_choice {item}")
        return returnDict
    
    def shac_statement_block(self, items):
        return "SHAC_CHOICE", items
    
    def hub_choice(self, items):
        returnDict = {"choice_description" : None, "condition" : None, "exit_instruction": None, "sequence" : None, "event_id" : None, "once" : False}
        for item in items:
            if type(item) == lark.Token:
                if item.type == "STATEMENT_DESCRIPTION":
                    returnDict["choice_description"] = item.value.strip()
                elif item.type == "EVENT_ID":
                    returnDict["event_id"] = item.value.strip().replace(" ", "_")
                elif item.type == "CHOICE_SINGLE":
                    returnDict["once"] = True
                elif item.type == "CHOICE_INFINITE":
                    returnDict["once"] = False
                else:
                    raise RuntimeError(f"Unexpected token {item.type} in hub_choice")
            elif type(item) == lark.Tree:
                if item.data == "condition":
                    returnDict["condition"] = _fix_cond_instr_str(item.children[0].value)
                elif item.data == "exit_instruction":
                    returnDict["exit_instruction"] = _fix_cond_instr_str(item.children[0].value)
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
        menuSlotMap = {"⇐" : "W", "⇑" : "N", "⇒" : "E", "⇓" : "S", "⇖" : "NW", "⇗" : "NE", "⇘" : "SE", "⇙" : "SW"}
        returnDict = {"menu_text" : None, "menu_slot" : None, "spoken_text" : None, "stage_directions" : None, "line_attributes" : {}, "condition" : None, "exit_instruction": None, "sequence" : None, "once": False}
        for item in items:
            if type(item) == lark.Token:
                if item.type == "MENU_TEXT":
                    returnDict["menu_text"] = item.value.strip()
                elif item.type == "MENU_SLOT":
                    returnDict["menu_slot"] = menuSlotMap[item.value.strip()]
                elif item.type == "SPOKEN_TEXT":
                    returnDict["spoken_text"] = item.value.strip()
                elif item.type == "STAGE_DIRECTIONS":
                    returnDict["stage_directions"] = item.value.strip("()").strip()
                elif item.type == "CHOICE_SINGLE":
                    returnDict["once"] = True
                elif item.type == "CHOICE_INFINITE":
                    returnDict["once"] = False
                else:
                    #logger.warning("Unexpected token in ")
                    raise RuntimeError(f"Unexpected token {item.type} in player_choice")
            elif type(item) == lark.Tree:
                if item.data == "condition":
                    returnDict["condition"] = _fix_cond_instr_str(item.children[0].value)
                elif item.data == "exit_instruction":
                    returnDict["exit_instruction"] = _fix_cond_instr_str(item.children[0].value)
                elif item.data == "inner_sequence":
                    returnDict["sequence"] = item.children
                # elif item.data == "line_attributes":
                #     usedKeys = []
                #     for lineAttrKey, lineAttrVal in item.children:
                #         if lineAttrKey in usedKeys:
                #             raise RuntimeError(f"Duplicate attribute '{lineAttrKey}' for line with text: '{returnDict['spoken_text']}'")
                #         usedKeys.append(lineAttrKey)
                #
                #         if lineAttrKey == "emotion" and lineAttrVal not in StatementTransformer.VALID_LINE_EMOTIONS:
                #             raise RuntimeError(f"Invalid attribute value '{lineAttrVal}' for attribute '{lineAttrKey}' for line with text: '{returnDict['spoken_text']}'")
                else:
                    raise RuntimeError(f"Unexpected tree {item.data} in player_choice")
            elif type(item) == dict and "line_attributes" in item:
                returnDict.update(item)
            else:
                raise RuntimeError(f"Unexpected type in player_choice {item}")
        return returnDict
    
    def player_choice_block(self, items):
        # items are already a list of choices
        return items
    
    def choice_dialog_statement(self, items):
        return "CHOICE_DIALOG", {"entity_name" : items[0].value.strip().replace(" ", "_"), "choices" : items[1]}
    
    def sequence(self, items):
        filteredItems = [item for item in items if type(item) == lark.Tree or  type(item) == lark.Token]
        if len(filteredItems) > 0:
            logger.warning(f"In sequence filtered the following: {filteredItems}")
        return [item for item in items if type(item) != lark.Tree or  type(item) != lark.Token]
    
    def if_block(self, items):
        return self.if_elseif(items)
    
    def if_elseif(self, items):
        elseSeq = None
        if len(items) == 3:
            if type(items[2]) == lark.Tree and items[2].data == "if_else":
                elseSeq = items[2].children[0].children
            else:
                elseSeq = [items[2]]
        
        ret =  "IF", {"eval_condition" : _fix_cond_instr_str(items[0].value), "sequence_true":items[1].children, "sequence_false": elseSeq}
        return ret

class NodeTransformer(lark.Transformer):
    
    def __init__(self, nodeDict):
        self.nodeDict = nodeDict
        super().__init__() 
        
    # def flags(self, items):
    #     print("=!!=")
    #     print(items)
    #     print("=!!=")
    #     return items
    
    def var_line(self, items):
        validationCriteria = {}
        if type( items[1]) == lark.Tree:
            defPlusEnumVals = [item.value for item in items[1].children]
            varType = "string"
            # remove quotes
            itemVal = defPlusEnumVals[0][1:-1]
            validationCriteria = {"is_one_of" : defPlusEnumVals[1:]}
        else:
            itemValStr = items[1].value
            if itemValStr.lower() == "true":
                varType = "bool"
                itemVal = True
            elif itemValStr.lower() == "false":
                varType = "bool"
                itemVal = False
            elif itemValStr.isdigit():
                varType = "int"
                itemVal = int(itemValStr)
            else:
                raise RuntimeError(f"Invalid value for variable {items[0].value}: {itemValStr}")
        retDict = {"variable_name" : items[0].value, "variable_default_value" : itemVal, "description" : None, "variable_type" : varType, "validation" : validationCriteria}
        if len(items) == 3:
            retDict["description"] = items[2].value.strip("(").strip(")")
        return retDict
    
    def node_body(self, items):
        nodeDict = self.nodeDict
        for item in items:
            # print("=============")
            # print(type(item))
            if type(item) == lark.Token:
                raise RuntimeError(f"Unexpected token {item.type} in node_body")
            elif type(item) == lark.Tree:
                if item.data == "start_sequence_lines":
                    nodeDict["start_sequence_lines"] = [c.value for c in item.children[0].children] # item.children[0]
                elif item.data == "referenced_sequences_lines":
                    nodeDict["referenced_sequences_lines"][item.children[0].value.strip()] = [c.value for c in item.children[1].children]
                elif item.data == "node_properties":
                    self._p_node_properties(item, nodeDict)
                elif item.data == "description_line":
                    nodeDict["description"] = item.children[0].value.strip()
                elif item.data == "description_block":
                    nodeDict["description"] = "\n".join([d.value.strip() for d in item.children])
                elif item.data == "variables":
                    nodeDict["variables"] = item.children
                elif item.data == "external_connections":
                    nodeDict["external_connections"] = [d.children[0].value.strip() for d in item.children]
                elif item.data == "external_variables":
                    nodeDict["external_variables"] = [d.children[0].value.strip() for d in item.children] 
                else:
                    raise RuntimeError(f"Unexpected tree {item.data} in node_body")
            else:
                raise RuntimeError(f"Unexpected type in node_definition {item}")
        return nodeDict

class DocTransformer(lark.Transformer):
    
    def start(self, items):
        return items
    
    # def _p_node_properties(self, node_prop, nodeDict):
    #     for item in node_prop.children:
    #         if item.data == "node_description":
    #             nodeDict["description"] = item.children[0].value.strip()
    #         if item.data == "image":
    #             nodeDict["image"] =item.children[0].value

    def node_definition(self, items):
        nodeDict = {"id" : None,
                    "node_type" : None,
                    "description": None,
                    "image" : None,
                    "variables" : [],
                    "external_variables" : [],
                    "external_connections" : [],
                    "start_sequence" : None,
                    "start_sequence_lines" : None,
                    "referenced_sequences": collections.OrderedDict(),
                    "referenced_sequences_lines" : collections.OrderedDict(),
                    "node_lines" : None}
        alias = None
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
                elif item.data == "node_lines":
                    nodeDict["node_lines"] = [c.value for c in item.children]
                elif item.data == "node_alias":
                    alias = item.children[0].value
                else:
                    raise RuntimeError(f"Unexpected tree {item.data} in node_definition")
            else:
                raise RuntimeError(f"Unexpected type in node_definition {item}")
        if alias is not None:
            nodeDict["id"] = alias
        return nodeDict
    
def _trans_seq_tree(seqId, NodeGrammar, sequenceLinesList):
    seqText = "\n".join(sequenceLinesList+[""])
    try:
        seqTree = lark.Lark(NodeGrammar, start='sequence', parser='lalr').parse(seqText)
        #print(seqTree.pretty())
        return StatementTransformer().transform(seqTree)
    except UnexpectedInput as le:
        #errMsg = traceback.format_exc(limit=1)
        if le.__context__ is not None and isinstance(le.__context__, UnexpectedInput):
            ce = le.__context__
        else:
            ce = le
        context = ce.get_context(seqText)
        logger.error(f"Failed to parse sequence §{seqId} because of an error on the following context and error:\n{context}\nError:\n{ce}")
        logger.info(f"Complete sequence text:\n{seqText}")
        return None
                

def parse(lines):
    cont = "\n".join(lines)
    errorCount = 0
        
    with open(os.path.join(_GRAMMAR_FOLDER, "doc_grammar.ebnf"), "r", encoding="utf-8") as f:
        DocGrammar = f.read()
    with open(os.path.join(_GRAMMAR_FOLDER, "node_grammar.ebnf"), "r", encoding="utf-8") as f:
        NodeGrammar = f.read()
    with open(os.path.join(_GRAMMAR_FOLDER, "sequence_grammar.ebnf"), "r", encoding="utf-8") as f:
        SequenceGrammar = f.read()
    
    docTree = lark.Lark(DocGrammar, start='start', parser='lalr').parse(cont)
    #print(docTree.pretty())
    
    nodes = DocTransformer().transform(docTree)
    
    ret = {"nodes": []}
    
    for node in nodes:
        #logger.info(f"Lexer processing node {node['id']}")
        nodelines = node["node_lines"]
        if nodelines[0].startswith("<IMAGE"):
            node["image"] = nodelines[0][7:-1]
            nodelines.pop(0)
        # if nodelines[0].lower().startswith("description"):
        #     node["description"] = nodelines[0].split(":")[1]
        #     nodelines.pop(0)
        nodelines.append("")
        nodeTxt = "\n".join(nodelines)
        try:
            nodeTree = lark.Lark(NodeGrammar, start='node_body', parser='earley').parse(nodeTxt)
            
            #print(nodeTree.pretty())
            #n = StatementTransformer().transform(nodeTree)
            n = NodeTransformer(node).transform(nodeTree)
            
            startSeq = _trans_seq_tree(node["id"]+"_start-sequence", SequenceGrammar, node["start_sequence_lines"])
            if startSeq == None:
                errorCount += 1
            else:
                n["start_sequence"] = startSeq
                
            for refSeqId in n["referenced_sequences_lines"]:
                rSeq = _trans_seq_tree(refSeqId, SequenceGrammar, n["referenced_sequences_lines"][refSeqId])
                if rSeq == None:
                    errorCount += 1
                else:
                    n["referenced_sequences"][refSeqId] = rSeq
            
            ret["nodes"].append(n)
            logger.info(f"Successfully parsed node {node['id']}")
        except UnexpectedInput as le:
            #errMsg = traceback.format_exc(limit=1)
            errorCount += 1
            if le.__context__ is not None and isinstance(le.__context__, UnexpectedInput):
                ce = le.__context__
            else:
                ce = le
            context = ce.get_context(nodeTxt)
            logger.error(f"Failed to parse node {node['id']} because of an error on the following context and error:\n{context}\n\nError:\n{ce}")
    
    if errorCount > 0:
        raise RuntimeError(f"Parsing failed with {errorCount} structural (lexing) errors")
    
    return ret

        
        
        # with open(os.path.join(_FILE_LOC, "grammar_defn"), "r") as f:
        #     fileCont = f.read()
        #
        # tree = lark.Lark(fileCont, start='start', parser='lalr', debug=True).parse(cont)
        #
        # n = StatementTransformer().transform(tree)
        # n = DocTransformer().transform(n)
        
        # print("=======\nChapter node:")
        # print_node("", n["chapter_node"])
        # print("=======\nNodes")
        # for restNode in n["nodes"]:
        #     print_node("", restNode)

    
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
