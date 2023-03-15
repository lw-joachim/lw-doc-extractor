'''
Created on 13 Jul 2022

@author: Joachim Kestner
'''
import json
import collections
import re
import logging
import binascii
import hashlib
import string

logger = logging.getLogger(__name__)

NODE_TITLE_MATCHER = re.compile("[^{]+{([^}])}")

VAR_NM_MATCHER = re.compile("[a-zA-Z_][a-zA-Z_0-9\.]*")

# id to an int counter
_idToOccurenceTracker = {}

VALID_DIGITS_FOR_ID = set()
VALID_DIGITS_FOR_ID.update(string.digits)
VALID_DIGITS_FOR_ID.update(string.ascii_letters)
VALID_DIGITS_FOR_ID.add("_")


def _format_string(inpStr, validDidgets):
    inpStr = "_".join(inpStr.split())
    return ''.join(c for c in inpStr if c in validDidgets)

def get_dialog_line_file_nm_lf(enityName, menuText, stage_directions, lineText):
    global _idToOccurenceTracker
    
    en = enityName.strip() if enityName else ""
    mt = menuText.strip() if menuText else ""
    lt = lineText.strip() if lineText else ""
    sd = stage_directions.strip() if stage_directions else ""
    
    crcStr1 = "{}#{}#{}".format(en, mt, lt)
    
    validIdsSet = set(VALID_DIGITS_FOR_ID)
    validIdsSet.add("#")
    
    resStr = _format_string(crcStr1, validIdsSet)
    
    acrc = binascii.crc32(crcStr1.encode("utf-8"))
    resHex = "{:08X}".format(acrc)
    retStr = "{}#{}".format(resHex, resStr)
    return  retStr

def get_dialog_line_id(chapterId, enityName, menuText, stage_directions, lineText):
    if chapterId == "LF":
        fileNm = get_dialog_line_file_nm_lf(enityName, menuText, stage_directions, lineText)
    else:
        
        en = enityName.strip() if enityName else ""
        mt = menuText.strip() if menuText else ""
        lt = lineText.strip() if lineText else ""
        
        fileNmWoHash = _format_string("{}_{}_{}_{}".format(chapterId, en, mt, lt), VALID_DIGITS_FOR_ID)
        hashedStr = hashlib.sha256(fileNmWoHash.encode("utf-8")).hexdigest()[:12].upper()
        
        fileNm = "{}_{}".format(hashedStr, fileNmWoHash)
    
    if len(fileNm) > 64:
        fileNm = fileNm[:64]
        
    if fileNm in _idToOccurenceTracker:
        num_occurances = _idToOccurenceTracker[fileNm]
        newRet = fileNm + "_" + str(num_occurances)
        _idToOccurenceTracker[fileNm] = num_occurances + 1
        fileNm = newRet
    else:
        _idToOccurenceTracker[fileNm] = 1
    
    return fileNm
    

def build_node_hierarchy(rootNodeId, nodeToDefnDict):
    nodeIdToParentIdDict = {}
    for k in nodeToDefnDict:
        if k == rootNodeId:
            continue
        hieraryParts = k.split("_")
        parent=rootNodeId
        if len(hieraryParts) > 1:
            parent = "_".join(hieraryParts[:-1])
        nodeIdToParentIdDict[k] = parent
    
    nodeIdToChildIdsDict = {}
    for nodeId, parentId in nodeIdToParentIdDict.items():
        if parentId not in nodeIdToChildIdsDict:
            nodeIdToChildIdsDict[parentId] = []
        nodeIdToChildIdsDict[parentId].append(nodeId)
    return nodeIdToParentIdDict, nodeIdToChildIdsDict

def get_processing_order(currNodeId, nodeIdToChildIdsDict):
    ret = [currNodeId]
    if currNodeId in nodeIdToChildIdsDict:
        for cNodeId in nodeIdToChildIdsDict[currNodeId]:
            ret.extend(get_processing_order(cNodeId, nodeIdToChildIdsDict))
    return ret

# # rules for automatically creating a link to a hub are
# #  - if last item in sequence is not a jump, choice, hub, if, shac, the_end or a node ref
# #  - then if this node, in the sequence it is embedded in, is not the last instruction in the sequence, then create a return
# #  - if not then link to the current nodes hub
# #  - if that doesnt exist then link to the hub in the parent or if parent is subsection then to the hub of the parent of subsection
# #  - if that doesnt exist raise an error
# def auto_link_hub(nodeId, sequenceDict, nodeToDefnDict, nodeIdToParentIdDict, allNodesWithOutgoingLinks):
#     parentId = nodeIdToParentIdDict[nodeId] if nodeId in nodeIdToParentIdDict else None
#
#     currentHub = _get_hub_id(nodeToDefnDict[nodeId])
#     parentHub = None
#     if parentId:
#         parentWithHubId = None
#         if nodeToDefnDict[parentId]["node_type"] == "SubSection":
#             parentWithHubId = nodeIdToParentIdDict[parentId] if parentId in nodeIdToParentIdDict else None
#         else:
#             parentWithHubId = parentId
#
#         if parentWithHubId:
#             parentHub = _get_hub_id(nodeToDefnDict[parentWithHubId])
#
#
#     for seqId in sequenceDict:
#         if len(sequenceDict[seqId]) == 0:
#             raise RuntimeError(f"Cannot fix sequence {seqId} as it is empty.")
#         if sequenceDict[seqId][-1][0] == "THE_END":
#             continue
#         if sequenceDict[seqId][-1][0] not in ["CHOICE_DIALOG", "IF", "HUB", "NODE_REF", "INTERNAL_JUMP", "EXTERNAL_JUMP", "THE_END", "GENERIC_HUB"]:
#             if nodeId in allNodesWithOutgoingLinks:
#                 sequenceDict[seqId].append(("INTERNAL_JUMP", {"referenced_id" : nodeId}))
#                 logger.debug(f"For sequence {seqId} adding internal return jump to {nodeId}")
#             elif currentHub != None:
#                 sequenceDict[seqId].append(("INTERNAL_JUMP", {"referenced_id" : currentHub}))
#                 logger.debug(f"For sequence {seqId} adding internal jump to {currentHub}")
#             elif parentHub != None:
#                 sequenceDict[seqId].append(("EXTERNAL_JUMP", {"referenced_id" : parentHub}))
#                 logger.debug(f"For sequence {seqId} adding external jump to {parentHub}")
#             else:
#                 raise RuntimeError(f"Cannot fix sequence {seqId}. Last command of sequence {sequenceDict[seqId][-1][0]}")
#
#
#
# # creates new sequences for instructions for hub, dialog choide and if and
# # replaces instructions with references
# def flatten_sequences(chapterNodeId, sequenceIds, nodeDefnDict):
#     complexStatements = ["CHOICE_DIALOG", "IF", "HUB", "SHAC_CHOICE"]
#
#     flatSequences = collections.OrderedDict()
#     nodeId = nodeDefnDict['id']
#
#     seqPos = {}
#
#     hubFound = False
#
#     addedOnceVars = []
#
#     for seqId in sequenceIds:
#         if seqId == "start_sequence":
#             seqToProcess = nodeDefnDict[seqId]
#             seqId = f"{nodeId}_start_sequence"
#         else:
#             seqToProcess = nodeDefnDict["referenced_sequences"][seqId]
#         if not seqId.startswith(nodeId):
#             raise RuntimeError(f"Sequence {seqId} does not start with prefix of node {nodeId}")
#
#         logger.debug(f"Flattenning sequence {seqId}")
#         flatSequences[seqId] = []
#         seqPos[seqId] = (len(seqPos), 0)
#         for i, inst in enumerate(seqToProcess):
#             instType = inst[0]
#             complexStatementUsed = False
#             if instType not in complexStatements:
#                 flatSequences[seqId].append(inst)
#             else:
#                 try:
#                     if complexStatementUsed:
#                         raise RuntimeError(f"There con only be one complex statement within a sequence. Offending statement: {inst}")
#                     if instType == "HUB":
#                         if hubFound:
#                             raise RuntimeError("More than one hub found in node {nodeDefnDict['id']}")
#                         hubFound = True
#                         if nodeDefnDict["node_type"] not in ["Chapter", "Section"]:
#                             raise RuntimeError(f"Node {nodeDefnDict['id']} defines a hub but is not of type Chapter or Section")
#
#                         hubSeqId = f"{nodeDefnDict['id']}_Hub"
#
#                         flatSequences[seqId].append(("INTERNAL_JUMP", {"referenced_id" :hubSeqId}))
#
#                         flatSequences[hubSeqId] = [["HUB", {"choices" : [], "original_sequence" : seqId if i == 0 else None}]]
#                         seqPos[hubSeqId] = (len(seqPos), 0)
#
#                         choices = []
#                         for cCount, choice in enumerate(inst[1]):
#                             choiceSeqId = f"{seqId}~{cCount}~hubchoice"
#                             choices.append({"sequence_ref": choiceSeqId})
#                             addInstr = ("GAME_EVENT_LISTENER", {"description": f"{choice['choice_description']}", "condition" : choice["condition"], "exit_instruction": choice["exit_instruction"], "event_id" : choice["event_id"]})
#                             if choice["once"]:
#                                 varNm = f"{chapterNodeId}.once_{choiceSeqId}".replace("-", "_").replace("~", "_")
#                                 addedOnceVars.append(varNm)
#                                 addInstr[1]["condition"] = choice["condition"] +  f" && {varNm} == false" if choice["condition"] else  f"{varNm} == false"
#                                 addInstr[1]["exit_instruction"] = choice["exit_instruction"] +  f"; {varNm} = true" if choice["exit_instruction"] else  f"{varNm} = true"
#                             flatSequences[choiceSeqId] = [addInstr] + choice["sequence"]
#                             seqPos[choiceSeqId] = (len(seqPos), 1)
#                         flatSequences[hubSeqId][0][1]["choices"] = choices
#
#                     elif instType == "CHOICE_DIALOG":
#                         choices = [dict(c) for c in inst[1]["choices"]]
#                         for cCount, choice in enumerate(choices):
#                             choiceSeqId = f"{seqId}~{cCount}~dialogchoice"
#                             flatSequences[choiceSeqId] = choice.pop("sequence")
#                             choice["sequence_ref"] = choiceSeqId
#                             if choice["once"]:
#                                 varNm = f"{chapterNodeId}.once_{choiceSeqId}".replace("-", "_").replace("~", "_")
#                                 addedOnceVars.append(varNm)
#                                 choice["condition"] = choice["condition"] + f" && {varNm} == false" if choice["condition"] else  f"{varNm} == false"
#                                 choice["exit_instruction"] = choice["exit_instruction"] +  f"; {varNm} = true" if choice["exit_instruction"] else  f"{varNm} = true"
#                             seqPos[choiceSeqId] = (len(seqPos), i+1)
#                         cpyDict = dict(inst[1])
#                         cpyDict["choices"] = choices
#                         flatSequences[seqId].append(("CHOICE_DIALOG",  cpyDict))
#                     elif instType == "SHAC_CHOICE":
#                         flatSequences[seqId].append(["GENERIC_HUB", {"choices" : [], "original_sequence" : None}])
#                         for cCount, choice in enumerate(inst[1]):
#                             choiceSeqId = f"{seqId}~{cCount}~shacchoice"
#                             flatSequences[seqId][-1][1]["choices"].append({"sequence_ref": choiceSeqId})
#                             addInstr = ("GAME_EVENT_LISTENER", {"description": f"{choice['choice_description']}", "condition" : None, "exit_instruction": None, "event_id" : choice["event_id"]})
#                             flatSequences[choiceSeqId] = [addInstr] + choice["sequence"]
#                             seqPos[choiceSeqId] = (len(seqPos), 1)
#
#                     elif instType == "IF":
#                         choiceSeqIdTrue = f"{seqId}~true"
#                         choiceSeqIdFalse = f"{seqId}~false"
#                         flatSequences[choiceSeqIdTrue] = inst[1]["sequence_true"]
#                         flatSequences[choiceSeqIdFalse] = inst[1]["sequence_false"]
#                         flatSequences[seqId].append(("IF", {"eval_condition": inst[1]["eval_condition"], "sequence_ref_true" : choiceSeqIdTrue, "sequence_ref_false" :choiceSeqIdFalse}))
#                         seqPos[choiceSeqIdTrue] = (len(seqPos), i+1)
#                         seqPos[choiceSeqIdFalse] = (len(seqPos), i+1)
#
#                     complexStatementUsed = True
#                 except Exception:
#                     logger.warning(f"Error occurred in sequence {seqId} while processing instruction {i}: {inst}")
#                     raise
#
#     return flatSequences, seqPos, addedOnceVars
#
# def _collapse_links(sequences, allNodeIds):
#     retDict = {}
#     def _collapse_internal(refNode):
#         seqList = sequences[refNode]
#         if len(seqList) == 1:
#             instType, instrPrmDict = seqList[0]
#             if instType == "INTERNAL_JUMP":
#                 return _collapse_internal(instrPrmDict["referenced_id"])
#             elif instType == "EXTERNAL_JUMP":
#                 return ("EXT", instrPrmDict["referenced_id"])
#         return ("INT", refNode)
#
#     for seqId, seqList in sequences.items():
#
#         if len(seqList) == 0:
#             raise RuntimeError(f"Sequence of len 0 found: {seqId}")
#
#         if len(seqList) == 1:
#             instType, instrPrmDict = seqList[0]
#             if instType == "EXTERNAL_JUMP":
#                 retDict[seqId] = ("EXT", instrPrmDict["referenced_id"])
#             elif instType == "INTERNAL_JUMP":
#                 retDict[seqId] = _collapse_internal(instrPrmDict["referenced_id"])
#     return retDict

def _isInstrTypeAllowed(nodeId, nodeType, currSequence, instrType):
    
    allowedEverywhere = ["COMMENT", "IF", "SET", "EXTERNAL_JUMP", "INTERNAL_JUMP"]
    if instrType in allowedEverywhere:
        return True
    
    if nodeType == "C-SEG":
        return False
    
    if nodeType in ["C-CUT", "C-SAC"]:
        if instrType == "DIALOG_LINE":
            return True
        if nodeType == "C-SAC":
            if instrType == "GENERIC_HUB" or instrType == "GAME_EVENT_LISTENER":
                return True
        return False
            
    if nodeType.startswith("D-"):
        if instrType == "DIALOG_LINE":
            return True
        if instrType == "CHOICE_DIALOG":
            return True
        return False
    
    if instrType == "DIALOG_LINE" or instrType == "CHOICE_DIALOG":
        return False

    if instrType == "HUB" and nodeType == "SubSection":
        return False
    
    if instrType == "HUB" and nodeType == "Chapter":
        return False
    
    return True

_EMBED_ALLOWED_LIST = ["Chapter", "Section", "SubSection"]

def _check_embedded_nodes(nodeId, nodeType, instructions, nodeIdToDefnDict, nodeIdToParentIdDict):
    for instrDict in instructions:
        if instrDict["instruction_type"] == "NODE_REF":
            refNodeId = instrDict["parameters"]["id"]
            embeddedType = nodeIdToDefnDict[refNodeId]["node_type"]
            
            if nodeIdToParentIdDict[refNodeId] != nodeId:
                raise RuntimeError(f"Node {refNodeId} is embedded in {nodeId}, but the parent hierarchy is incorrect. Check '_' usage")
            
            if nodeType not in _EMBED_ALLOWED_LIST:
                raise RuntimeError(f"Node {nodeId} embeds node {refNodeId}, but its of node type {nodeType} which cant embed other nodes")
            
            if nodeType == "Chapter" and embeddedType == "SubSection":
                raise RuntimeError(f"Chapter node {nodeId} embeds node of type SubSection {refNodeId} which is not allowed")
                
            if nodeType == "SubSection" and embeddedType == "SubSection":
                raise RuntimeError(f"SubSection node {nodeId} embeds node of type SubSection {refNodeId} which is not allowed")
            
            if nodeType == "SubSection" and embeddedType == "Section":
                raise RuntimeError(f"SubSection node {nodeId} embeds node of type Section {refNodeId} which is not allowed")

def process_instruction(chapterNodeId, instructionId, intructionType, instructionParameterDictionary):
    processedInstruction = None
    addedOnceVars = set()
    customPinsForSubSequenceMap = {}
    subSequencesMap = collections.OrderedDict()
    if intructionType =="CHOICE_DIALOG":
        choices = [dict(c) for c in instructionParameterDictionary["choices"]]
        choiceSequenceIds = []
        for cCount, choice in enumerate(choices):
            choiceSeqId = f"{instructionId}_dc{cCount}"
            choiceSequenceIds.append(choiceSeqId)
            if choice["once"]:
                varNm = f"{chapterNodeId}.once_{choiceSeqId}".replace("-", "_").replace("~", "_")
                addedOnceVars.add(varNm)
                choice["condition"] = choice["condition"] + f" && {varNm} == false" if choice["condition"] else  f"{varNm} == false"
                choice["exit_instruction"] = choice["exit_instruction"] +  f"; {varNm} = true" if choice["exit_instruction"] else  f"{varNm} = true"
            
            choiceInstrPrm = {"entity_name": instructionParameterDictionary["entity_name"], "menu_text" : choice["menu_text"], "spoken_text": choice["spoken_text"], "stage_directions" : choice["stage_directions"], "line_attributes" : choice["line_attributes"], "condition": choice["condition"], "exit_instruction": choice["exit_instruction"]}
            extCId = get_dialog_line_id(chapterNodeId, instructionParameterDictionary["entity_name"], choice["menu_text"], choice["stage_directions"], choice["spoken_text"])
            choiceInternalId = choiceSeqId+"_init"+str(choiceSeqId)
            instrDict = {"instruction_type" : "DIALOG_LINE", "internal_id" : choiceInternalId, "parameters" : choiceInstrPrm, "external_id": extCId}

            subSequencesMap[choiceSeqId] = (choice["sequence"], instrDict)
    elif intructionType == "HUB":
        hubInstrPrms = {"hub_name" : f"{chapterNodeId}_HUB"}
        processedInstruction = {"instruction_type" : "HUB", "internal_id" : instructionId, "parameters" : hubInstrPrms, "external_id": None}
        
        # note for HUB instructionParameterDictionary is a list of choices :(
        for cCount, choice in enumerate(instructionParameterDictionary):
            choiceSeqId = f"{instructionId}_hc{cCount}"
            coiceInstrDict = {"description": f"{choice['choice_description']}", "condition" : choice["condition"], "exit_instruction": choice["exit_instruction"], "event_id" : choice["event_id"]}
            
            if choice["once"]:
                varNm = f"{chapterNodeId}.once_{choiceSeqId}".replace("-", "_").replace("~", "_")
                addedOnceVars.add(varNm)
                coiceInstrDict["condition"] = choice["condition"] +  f" && {varNm} == false" if choice["condition"] else  f"{varNm} == false"
                coiceInstrDict["exit_instruction"] = choice["exit_instruction"] +  f"; {varNm} = true" if choice["exit_instruction"] else  f"{varNm} = true"
            choiceInternalId = choiceSeqId+"_gel"+str(choiceSeqId)
            choiceInstrDict = {"instruction_type" : "GAME_EVENT_LISTENER", "internal_id" : choiceInternalId, "parameters" : coiceInstrDict, "external_id" : None}
            
            subSequencesMap[choiceSeqId] = (choice["sequence"], choiceInstrDict)
    elif intructionType == "IF":
        choiceSeqIdTrue = f"{instructionId}_true"
        choiceSeqIdFalse = f"{instructionId}_false"
        
        subSequencesMap[choiceSeqIdTrue] = (instructionParameterDictionary["sequence_true"], None)
        subSequencesMap[choiceSeqIdFalse] = (instructionParameterDictionary["sequence_false"], None)
        
        customPinsForSubSequenceMap[choiceSeqIdFalse] = 1
        
        ifInstrPrms = {"eval_condition": instructionParameterDictionary["eval_condition"]}
        processedInstruction = {"instruction_type" : intructionType, "internal_id" : instructionId, "parameters" : ifInstrPrms, "external_id": None}
        
    elif intructionType == "SHAC_CHOICE":
        processedInstruction = {"instruction_type" : "GENERIC_HUB", "internal_id" : instructionId, "parameters" : {"hub_name" : "shac_choice"}, "external_id": None}
        # note for HUB instructionParameterDictionary is a list of choices :(
        for cCount, choice in enumerate(instructionParameterDictionary):
            choiceSeqId = f"{instructionId}_sc{cCount}"
            coiceInstrDict = {"description": f"{choice['choice_description']}", "condition" : None, "exit_instruction": None, "event_id" : choice["event_id"]}
            #coiceInstrDict = {"description": f"{choice['choice_description']}", "condition" : choice["condition"], "exit_instruction": choice["exit_instruction"], "event_id" : choice["event_id"]}
            # if choice["once"]:
            #     varNm = f"{chapterNodeId}.once_{choiceSeqId}".replace("-", "_").replace("~", "_")
            #     addedOnceVars.append(varNm)
            #     coiceInstrDict["condition"] = choice["condition"] +  f" && {varNm} == false" if choice["condition"] else  f"{varNm} == false"
            #     coiceInstrDict["exit_instruction"] = choice["exit_instruction"] +  f"; {varNm} = true" if choice["exit_instruction"] else  f"{varNm} = true"
            choiceInternalId = choiceSeqId+"_gel"
            choiceInstrDict = {"instruction_type" : "GAME_EVENT_LISTENER", "internal_id" : choiceInternalId, "parameters" : coiceInstrDict, "external_id": None}
            subSequencesMap[choiceSeqId] = (choice["sequence"], choiceInstrDict)
    else:
        if intructionType == "NODE_REF":
            extId = instructionParameterDictionary["id"]
        elif intructionType == "DIALOG_LINE":
            entNm = instructionParameterDictionary["entity_name"]
            entTxt = instructionParameterDictionary["spoken_text"]
            nmuTxt = instructionParameterDictionary["menu_text"]
            dsTxt = instructionParameterDictionary["stage_directions"]
            extId = get_dialog_line_id(chapterNodeId, entNm, nmuTxt, dsTxt, entTxt)
        else:
            extId = None
        
        processedInstruction = {"instruction_type" : intructionType, "internal_id" : instructionId, "parameters" : instructionParameterDictionary, "external_id": extId}
    
    return processedInstruction, addedOnceVars, subSequencesMap, customPinsForSubSequenceMap

class InstructionsContainer:
    
    def __init__(self):
        self.instrXPos = 0
        self.instructions = []
        self.positions = []
        self.currYRow = 0
        self.currSeqAddY = 0
        self.maxYPos = 0
        self.currSeqMaxX = 0
        
    def add_instruction(self, instruction):
        self.instructions.append(instruction)
        self.positions.append((self.instrXPos, self.currYRow))
        self.instrXPos += 1
            
    def reset_x(self):
        if self.instrXPos > 0 or self.currSeqAddY != 0:
            self.instrXPos = 0
            self.currSeqMaxX = 0
            self.currSeqAddY = 0
            self.currYRow = self.maxYPos + 1
            self.maxYPos = self.currYRow
    
    def add_instructions_of_sequence(self, seqInstructions, seqPositions, resetX=False):
        if len(seqInstructions) != len(seqPositions):
            raise RuntimeError("Unequal length sequence instruction & position arrays")
        if resetX:
            self.reset_x()
        self.instructions.extend(seqInstructions)
        
        for sdx, sdy in seqPositions:
            seqPosX = self.instrXPos + sdx
            seqPosY = self.currYRow + self.currSeqAddY + sdy
            self.positions.append((seqPosX, seqPosY))
            if seqPosY > self.maxYPos:
                self.maxYPos = seqPosY
            if seqPosX > self.currSeqMaxX:
                self.currSeqMaxX = seqPosX
        self.currSeqAddY += 1
        
    def finished_adding_sequences(self):
        if self.currSeqMaxX > 0:
            self.instrXPos = self.currSeqMaxX + 1
        self.currSeqAddY = 0
        self.currSeqMaxX = 0
    
    def get_instructions_and_positions(self):
        if len(self.instructions) != len(self.positions):
            raise RuntimeError("Unequal length instruction & position arrays")
        return self.instructions, self.positions
    
    def get_instructions(self):
        return self.instructions
    
    def __len__(self):
        return len(self.instructions)

def process_sequence(chapterNodeId, nodeId, sequenceId, instructionList, initialSequnceInstruction):  
    # Deleted todos:
    #  - removed allowed types check
    
    instructions = InstructionsContainer()
    
    internalLinks = []
    
    internalJumpsToProcess = []
    externalJumpsToProcess = []
    if initialSequnceInstruction:
        instructions.add_instruction(initialSequnceInstruction)
    currIntNode = "{}_{}".format(sequenceId, "sqStart")
    #instructions.add_instruction({"instruction_type" : "SEQUENCE_NODE", "internal_id" : currIntNode, "parameters" : {"sequence_name":sequenceId}, "external_id": sequenceId})
    instructions.add_instruction({"instruction_type" : "SET", "internal_id" : currIntNode, "parameters" : {"instruction":"//"+sequenceId}, "external_id": None})
    if initialSequnceInstruction:
        internalLinks.append((initialSequnceInstruction["internal_id"], 0, currIntNode))
    
    addedOnceVars = set()
    
    previousSequencesToContinueOnFrom = {}
    
    numberOfInstructions = len(instructionList)
    
    lastWasJumpOrEnd = False
    
    for i, aInstr in enumerate(instructionList):
        instType, instrPrmDict = aInstr
        
        if lastWasJumpOrEnd:
            raise RuntimeError(f"Cannot continue after a jump or 'the end' in sequence {sequenceId}")
        lastWasJumpOrEnd = False
        
        processedInstruction = None
        newAddedOnceVars = set()
        newSequences = {}
        customPinsForSubSequenceMap = {}
        
        if currIntNode == None and len(previousSequencesToContinueOnFrom) == 0:
            raise RuntimeError("No current node and no sequences to continue on from")
        
        if instType == "INTERNAL_JUMP" or instType == "EXTERNAL_JUMP":
            if currIntNode == None:
                internal_id = sequenceId+"_"+str(len(instructions))
                instructions.add_instruction({"instruction_type" : "SET", "internal_id" : internal_id, "parameters" : {"instruction" : "//dummy to have something to connect to before a jump"}, "external_id": None})
                currIntNode = internal_id
                if len(previousSequencesToContinueOnFrom) > 0:
                    for _seqId, prevSeqEndIntIdList in previousSequencesToContinueOnFrom.items():
                        for prevSeqEndIntId in prevSeqEndIntIdList:
                            internalLinks.append((prevSeqEndIntId, 0, currIntNode))
                    previousSequencesToContinueOnFrom.clear()
            if instType == "INTERNAL_JUMP":
                internalJumpsToProcess.append((currIntNode, 0, instrPrmDict["referenced_id"]))
            elif instType == "EXTERNAL_JUMP":
                externalJumpsToProcess.append((currIntNode, 0, instrPrmDict["referenced_id"]))
            
            lastWasJumpOrEnd = True
            continue
        
        elif instType == "HUB":
            if i < numberOfInstructions-1:
                raise RuntimeError("Hub needs to be the last instruction in a sequence")
            hubSeqId = f"{nodeId}_Hub"
            hubIntId = hubSeqId+"_0"
            #internalJumpsToProcess.append((currIntNode, 0, hubSeqId))
            
            processedInstruction, newAddedOnceVars, newSequences, customPinsForSubSequenceMap = process_instruction(chapterNodeId, hubIntId, instType, instrPrmDict)

            # hubSeqNodeInstrDict = {"instruction_type" : "SEQUENCE_NODE", "internal_id" : hubIntId, "parameters" : {"sequence_name":hubSeqId}, "external_id": hubSeqId}
            # newSequences[hubSeqId] = ([hubSeqNodeInstrDict, processedInstruction], None)
            # newSequences.update(newSubSequenceMap)
            
            
        else:
            instrId = "{}_{}".format(sequenceId, i)
            processedInstruction, newAddedOnceVars, newSequences, customPinsForSubSequenceMap = process_instruction(chapterNodeId, instrId, instType, instrPrmDict)
            if instType == "THE_END":
                lastWasJumpOrEnd = True
                
        addedOnceVars.update(newAddedOnceVars)
        
        if processedInstruction != None:
            instructions.add_instruction(processedInstruction)
            
            if len(previousSequencesToContinueOnFrom) > 0:
                for _seqId, prevSeqEndIntIdList in previousSequencesToContinueOnFrom.items():
                    for prevSeqEndIntId in prevSeqEndIntIdList:
                        internalLinks.append((prevSeqEndIntId, 0, processedInstruction["internal_id"]))
                previousSequencesToContinueOnFrom.clear()
            elif currIntNode != None:
                internalLinks.append((currIntNode, 0, processedInstruction["internal_id"]))
            else:
                raise RuntimeError("Can't attach {processedInstruction['internal_id']} to a previous node(s)")
            currIntNode = processedInstruction["internal_id"]
            
        
        newSeqToContinueOnFrom = {}
        for newSeqId in newSequences:
            seqRawInstructions, initialInstr = newSequences[newSeqId]
            seqInstructions, seqInstrPos, seqInternalLinks, seqIntJumps, seqExternalJumps, seqEndTrailingInternalIds, newSeqAddedOnceVars = process_sequence(chapterNodeId, nodeId, newSeqId, seqRawInstructions, initialInstr)
            
            # TODO add check that there are either no links or no trailing sequences? or check emebed
            
            newSeqToContinueOnFrom[newSeqId] = seqEndTrailingInternalIds
            
            instructions.add_instructions_of_sequence(seqInstructions, seqInstrPos)
            internalLinks.extend(seqInternalLinks)
            internalJumpsToProcess.extend(seqIntJumps)
            externalJumpsToProcess.extend(seqExternalJumps)
            addedOnceVars.update(newSeqAddedOnceVars)
            
            ssPinIdx  = 0 if newSeqId not in customPinsForSubSequenceMap else customPinsForSubSequenceMap[newSeqId]
            newSeqStartInstrIntId = seqInstructions[0]["internal_id"]
            
            if currIntNode != None:
                internalLinks.append((currIntNode, ssPinIdx, newSeqStartInstrIntId))
            else:
                if len(previousSequencesToContinueOnFrom) == 0:
                    raise RuntimeError("No previous to continue on from")
                for _seqId, prevSeqEndIntIdList in previousSequencesToContinueOnFrom.items():
                    for prevSeqEndIntId in prevSeqEndIntIdList:
                        internalLinks.append((prevSeqEndIntId, 0, newSeqStartInstrIntId))
        instructions.finished_adding_sequences()

        if len(newSeqToContinueOnFrom) > 0:
            currIntNode = None
            previousSequencesToContinueOnFrom = newSeqToContinueOnFrom
    
    if lastWasJumpOrEnd:
        endTrailingInternalIds = []
    else:
        if currIntNode != None:
            endTrailingInternalIds = [currIntNode]
        if len(previousSequencesToContinueOnFrom) > 0:
            endTrailingInternalIds = []
            for seqId in previousSequencesToContinueOnFrom:
                endTrailingInternalIds.extend(previousSequencesToContinueOnFrom[seqId])
    
    instrArr, posArray = instructions.get_instructions_and_positions()
    return  instrArr, posArray, internalLinks, internalJumpsToProcess, externalJumpsToProcess, endTrailingInternalIds, addedOnceVars
    
        
# rules for automatically creating a link to a hub are
#  - if the instruction does not contain a link
#  - then if this node is an embedded node (in the sequence it is embedded in, is not the last instruction in the sequence) then create a return
#  - if not then link to the current nodes hub
#  - if that doesnt exist then link to the hub in the parent or if parent is subsection then to the hub of the parent of subsection
#  - if that doesnt exist raise an error
def fix_int_jumps_and_trailing_instr(nodeId, instructions, intLinks, internalJumpsToProcess, extJumps, sequenceIdToIntId, nodeToDefnDict, nodeIdToParentIdDict, isEmbedded):
    newLinks = []
    newExtLinks = []
    
    parentId = nodeIdToParentIdDict[nodeId] if nodeId in nodeIdToParentIdDict else None
    
    currentHub = _get_hub_id(nodeToDefnDict[nodeId])
    parentHub = None
    if parentId:
        parentWithHubId = None
        if nodeToDefnDict[parentId]["node_type"] == "SubSection":
            parentWithHubId = nodeIdToParentIdDict[parentId] if parentId in nodeIdToParentIdDict else None
        else:
            parentWithHubId = parentId
        
        if parentWithHubId:
            parentHub = _get_hub_id(nodeToDefnDict[parentWithHubId])
            
    # if currentHub and nodeId in allNodesWithOutgoingLinks:
    #     raise RuntimeError("Embedded node {} has a hub")
    
    startSeqNm = f"{nodeId}_start_sequence"
    newLinks.append((nodeId, 0, sequenceIdToIntId[startSeqNm]))
            
    for srcInternId, sourceOutPin, targetSequennce in internalJumpsToProcess:
        if targetSequennce == "CONTINUE":
            if not isEmbedded:
                raise RuntimeError(f"Using a CONTINUE jump in a non embed node {nodeId}")
            newLinks.append((srcInternId, sourceOutPin, nodeId))
        elif targetSequennce in sequenceIdToIntId:
            newLinks.append((srcInternId, sourceOutPin, sequenceIdToIntId[targetSequennce]))
        else:
            logger.warn(f"{targetSequennce} not found. Available internal sequences for node id {nodeId} are {sequenceIdToIntId}")
            raise RuntimeError(f"In node {nodeId} cannot create an internal link from {srcInternId} to {targetSequennce}")
        
    
    intIdWithLink = [srcIntId for srcIntId, _srcPinIdx, _tarIntId in intLinks]
    intIdWithLink.extend([srcIntId for srcIntId, _srcPinIdx, _tarSeq in newLinks])
    intIdWithLink.extend([srcIntId for srcIntId, _srcPinIdx, _tarSeq in extJumps]) 
    intIdWithLinkSet = set(intIdWithLink)
    embeddedNodes = []
    
    #print(json.dumps(instructions, indent=2))
    #print(json.dumps(intLinks, indent=2))
    for instr in instructions:
        instrType = instr["instruction_type"]
        instrId = instr["internal_id"]
        if instrType == "THE_END":
            if instrId in intIdWithLinkSet:
                raise RuntimeError(f"THE_END node should not have outgoing links. In node {nodeId}")
            continue
        elif instrType == "NODE_REF":
            if instrId in intIdWithLinkSet:
                embeddedNodes.append(instr["parameters"]["id"])
        else:
            if instrId in intIdWithLinkSet:
                continue
            # Trailing node found
            logger.debug(f"Node with instruction id '{instrId}' is trailing. Trying to generate link.")
            if currentHub != None:
                newLinks.append((instrId, 0, sequenceIdToIntId[currentHub]))
                logger.debug(f"For instruction with ID '{instrId}' adding internal jump to {currentHub}")
            elif isEmbedded:
                newLinks.append((instrId, 0, nodeId))
                logger.debug(f"For instruction with ID '{instrId}' adding internal return jump to {nodeId}")
            elif parentHub != None:
                newExtLinks.append((instrId, 0, parentHub))
                logger.debug(f"For instruction with ID '{instrId}' adding external jump to {parentHub}")
            else:
                raise RuntimeError(f"Cannot link trailing instruction with ID '{instrId}'. Not embedded and no hub to link to")
    return newLinks, newExtLinks, embeddedNodes

def process_node(chapterNodeId, nodeId, parentId, childIds, isEmbedded, nodeIdToDefnDict, nodeIdToParentIdDict, allNodeIds):
    nodeDefnDict = nodeIdToDefnDict[nodeId]
    
    seqNameToSeqInstrDict = {}
    seqNameToSeqInstrDict[f"{nodeId}_start_sequence"] = nodeDefnDict["start_sequence"]
    seqNameToSeqInstrDict.update(nodeDefnDict["referenced_sequences"])
    
    sequenceToIntId = {}
    instrContainer = InstructionsContainer()
    allIntLinks = []
    allExternalLinks = []
    allAddedOnceVars = set()
    
    try:
        intJumpsToProcess = []
        for sequenceId in seqNameToSeqInstrDict:
            seqRawInstructions = seqNameToSeqInstrDict[sequenceId]
            seqInstructions, seqInstructionPositions, seqInternalLinks, seqIntJumps, seqExternalJumps, _seqEndTrailingInternalIds, addedOnceVars = process_sequence(chapterNodeId, nodeId, sequenceId, seqRawInstructions, initialSequnceInstruction=None)
            sequenceToIntId[sequenceId] = seqInstructions[0]["internal_id"]
            instrContainer.add_instructions_of_sequence(seqInstructions, seqInstructionPositions, resetX=True)
            allIntLinks.extend(seqInternalLinks)
            intJumpsToProcess.extend(seqIntJumps)
            allExternalLinks.extend(seqExternalJumps)
            allAddedOnceVars.update(addedOnceVars)
        instrContainer.finished_adding_sequences()
            
        hubs = [instr["internal_id"] for instr in instrContainer.get_instructions() if instr["instruction_type"] == "HUB"]
        childNodes = [instr["external_id"] for instr in instrContainer.get_instructions() if instr["instruction_type"] == "NODE_REF"]
        
        if len(hubs) > 1:
            raise RuntimeError(f"Node {nodeId} has more than 1 hub")
        elif len(hubs) == 1:
            sequenceToIntId[f"{nodeId}_Hub"] = hubs[0]
            
        newIntLinks, newExtLinks, embeddedNodes = fix_int_jumps_and_trailing_instr(nodeId, instrContainer.get_instructions(), allIntLinks, intJumpsToProcess, allExternalLinks, sequenceToIntId, nodeIdToDefnDict, nodeIdToParentIdDict, isEmbedded)
        allIntLinks.extend(newIntLinks)
        allExternalLinks.extend(newExtLinks)
        
        
        nodesReferenced = []
        for childNode in childNodes:
            if childNode not in childIds:
                raise RuntimeError(f"{childNode} node reference does not match child nodes. Needs to be one of {childIds}")
            if childNode in nodesReferenced:
                raise RuntimeError(f"{childNode} node reference has been used twice in node {nodeId}")
            nodesReferenced.append(childNode)
            
        for cId in childIds:
            if cId not in nodesReferenced:
                logger.debug(f"{cId} not referenced in parent sequences. Creating island node in {nodeDefnDict['id']}.")
                internal_id = nodeId+"_"+str(len(instrContainer))
                if cId not in allNodeIds:
                    raise RuntimeError(f"Unknown node reference {cId}")
                instrDict = {"instruction_type" : "NODE_REF", "internal_id" : internal_id, "parameters" : {"id" : cId}, "external_id": cId}
                instrContainer.reset_x()
                instrContainer.add_instruction(instrDict)
        
        allInstructions, allInstructionPositions = instrContainer.get_instructions_and_positions()
        resDict = { "id": nodeDefnDict["id"],
                    "type": nodeDefnDict["node_type"],
                    "description": nodeDefnDict["description"],
                    "image" : nodeDefnDict["image"],
                    "parent" : parentId,
                    "internal_content_positions" : allInstructionPositions,
                    "internal_content": allInstructions,
                    "internal_links": allIntLinks,
                    "external_links": allExternalLinks,
                    "target_to_internal_id" : { seqId : tarIntId for seqId, tarIntId in sequenceToIntId.items() if "~" not in seqId},
                    "target_to_multiple_internal_id" : {} }
        if len(addedOnceVars) > 0:
            logger.debug(f"Added {len(addedOnceVars)} variable for options that will only be used once")
        return resDict, allAddedOnceVars, embeddedNodes
    except Exception as e:
        logger.warning(f"Error while processing node {nodeId}")
        raise

# def process_node_old(chapterNodeId, nodeId, parentId, childIds, embedSequenceWithOutlinksTracker, nodeIdToDefnDict, nodeIdToParentIdDict, allNodeIds):
#     nodeDefnDict = nodeIdToDefnDict[nodeId]
#     # array to keep track of nodes that have been referenced to determine which have not
#     nodesReferenced = []
#
#     # print("======!!!!!!")
#     # print(nodeId)
#     # print(json.dumps(nodeDefnDict, indent=2))
#
#     try:
#
#         sequenceIds = ["start_sequence"]
#         for k in nodeDefnDict["referenced_sequences"]:
#             sequenceIds.append(k)
#
#         flattenedSequences , sequenceStartPos, addedOnceVars = flatten_sequences(chapterNodeId, sequenceIds, nodeDefnDict)
#         #print(json.dumps(flattenedSequences, indent=2))
#         sequenceStartPos = {}
#
#         embedSequenceWithOutlinksTracker.update(_get_all_nodes_with_outgoing_links_in_sequences(flattenedSequences.values()))
#
#         # inplace
#         auto_link_hub(nodeId, flattenedSequences, nodeIdToDefnDict, nodeIdToParentIdDict, embedSequenceWithOutlinksTracker)
#
#         instructions = []
#         instructionPos = []
#         internalLinks = []
#         externalLinks = []
#
#         seqenceToNodeIntId = {}
#         sequenceToMultipleIntId = {}
#
#         collapsedSequenceIdToTarget = _collapse_links(flattenedSequences, allNodeIds)
#         # print("==== Collapsed list")
#         # print(json.dumps(collapsedSequenceIdToTarget, indent =2 ))
#
#         currIntNode = nodeId
#
#         jumpsToProcess = []
#         anonChoicesThatCanBeLinkedTo = []
#
#         seqPosX = 0
#         seqPosY = 0
#         intrPosCnt = 0
#
#         maxYPos = 0
#
#         # print("================= {} collaped seq".format(nodeId))
#         # print(collapsedSequenceIdToTarget)
#         # print("====================== collaped end")
#
#
#
#         for seqId, seqList in flattenedSequences.items():
#             if seqId in collapsedSequenceIdToTarget and not seqId.endswith("start_sequence"):
#             #if seqId in collapsedSequenceIdToTarget:
#                 continue
#
#             if seqId in sequenceIds:
#                 intrPosCnt = 0
#                 seqPosX = 0
#
#             if seqId in sequenceStartPos:
#                 seqPosX, seqPosY = sequenceStartPos[seqId]
#             else:
#                 if seqPosY > maxYPos:
#                     seqPosY = maxYPos
#
#             sequenceId = seqId
#             shouldBeDone = False
#
#             for instType, instrPrmDict in seqList:
#                 if shouldBeDone:
#                     raise RuntimeError(f"In sequence {seqId} instruction following a jump")
#                 shouldBeDone = True
#
#                 if not _isInstrTypeAllowed(nodeId, nodeDefnDict["node_type"], seqId, instType):
#                     raise RuntimeError(f"In sequence {seqId}, instruction type {instType} is not allowed within node type {nodeDefnDict['node_type']}")
#
#                 if instType == "INTERNAL_JUMP":
#                     jumpsToProcess.append((currIntNode, 0, instrPrmDict["referenced_id"]))
#                 elif instType == "EXTERNAL_JUMP":
#                     externalLinks.append((currIntNode, 0, instrPrmDict["referenced_id"]))
#                 elif instType =="CHOICE_DIALOG":
#                     childIntIds = []
#                     for cDict in instrPrmDict["choices"]:
#                         internal_id = nodeId+"_"+str(len(instructions))
#                         childIntIds.append(internal_id)
#                         choiceInstrPrm = {"entity_name": instrPrmDict["entity_name"], "menu_text" : cDict["menu_text"], "spoken_text": cDict["spoken_text"], "stage_directions" : cDict["stage_directions"], "line_attributes" : cDict["line_attributes"], "condition": cDict["condition"], "exit_instruction": cDict["exit_instruction"]}
#                         extCId = get_dialog_line_id(chapterNodeId, instrPrmDict["entity_name"], cDict["menu_text"], cDict["stage_directions"], cDict["spoken_text"])
#                         instrDict = {"instruction_type" : "DIALOG_LINE", "internal_id" : internal_id, "parameters" : choiceInstrPrm, "external_id": extCId}
#                         instructions.append(instrDict)
#                         instructionPos.append((seqPosX+intrPosCnt, seqPosY))
#                         sequenceStartPos[cDict["sequence_ref"]] = (seqPosX+intrPosCnt+1, seqPosY)
#                         seqPosY += 1
#                         if currIntNode:
#                             internalLinks.append((currIntNode, 0, internal_id))
#                         else:
#                             anonChoicesThatCanBeLinkedTo.append((seqId, internal_id))
#                         jumpsToProcess.append((internal_id, 0, cDict["sequence_ref"]))
#                     intrPosCnt += 1
#
#                     if sequenceId != None:
#                         sequenceToMultipleIntId[sequenceId] = childIntIds
#                 else:
#                     intrPosAddX = 1
#                     intrPosY = seqPosY
#                     internal_id = nodeId+"_"+str(len(instructions))
#                     instrPrms = instrPrmDict
#                     extId = None
#                     if instType == "IF":
#                         jumpsToProcess.append((internal_id, 0, instrPrmDict["sequence_ref_true"]))
#                         jumpsToProcess.append((internal_id, 1, instrPrmDict["sequence_ref_false"]))
#                         instrPrms = {"eval_condition": instrPrmDict["eval_condition"]}
#                         sequenceStartPos[instrPrmDict["sequence_ref_true"]] = (seqPosX+intrPosCnt+1, seqPosY)
#                         seqPosY += 1
#                         sequenceStartPos[instrPrmDict["sequence_ref_false"]] = (seqPosX+intrPosCnt+1, seqPosY)
#                         intrPosAddX = 2
#                     elif instType == "HUB":
#                         for c in instrPrmDict["choices"]:
#                             jumpsToProcess.append((internal_id, 0, c["sequence_ref"]))
#                             sequenceStartPos[c["sequence_ref"]] = (seqPosX+intrPosCnt+1, seqPosY)
#                             seqPosY += 1
#                         instrPrms = {"hub_name" : f"{nodeId}_HUB"}
#                         if instrPrmDict["original_sequence"]:
#                             seqenceToNodeIntId[instrPrmDict["original_sequence"]] = internal_id
#                         intrPosAddX = 2
#                     elif instType == "GENERIC_HUB":
#                         for c in instrPrmDict["choices"]:
#                             jumpsToProcess.append((internal_id, 0, c["sequence_ref"]))
#                             sequenceStartPos[c["sequence_ref"]] = (seqPosX+intrPosCnt+1, seqPosY)
#                             seqPosY += 1
#                         instrPrms = {"hub_name" : f"{internal_id}_HUB"}
#                         intrPosAddX = 2
#                     elif instType == "NODE_REF":
#                         if instrPrmDict["id"] not in allNodeIds:
#                             raise RuntimeError(f"Unknown node reference {instrPrmDict['id']}")
#                         if instrPrmDict["id"] in nodesReferenced:
#                             raise RuntimeError(f"Node {instrPrmDict['id']} has been reference twice")
#
#                         nodesReferenced.append(instrPrmDict["id"])
#                         extId = instrPrmDict["id"]
#                     elif instType == "DIALOG_LINE":
#                         entNm = instrPrmDict["entity_name"]
#                         entTxt = instrPrmDict["spoken_text"]
#                         nmuTxt = instrPrmDict["menu_text"]
#                         dsTxt = instrPrmDict["stage_directions"]
#                         extId = get_dialog_line_id(chapterNodeId, entNm, nmuTxt, dsTxt, entTxt)
#
#                     instrDict = {"instruction_type" : instType, "internal_id" : internal_id, "parameters" : instrPrms, "external_id": extId}
#                     instructions.append(instrDict)
#                     instructionPos.append((seqPosX+intrPosCnt, intrPosY))
#                     intrPosCnt += intrPosAddX
#                     if currIntNode:
#                         internalLinks.append((currIntNode, 0, internal_id))
#                     if sequenceId:
#                         seqenceToNodeIntId[sequenceId] = internal_id
#
#                     sequenceId = None
#
#                     currIntNode = internal_id
#
#                 shouldBeDone = instType in ["HUB", "IF", "INTERNAL_JUMP", "EXTERNAL_JUMP", "CHOICE_DIALOG"]
#
#             seqPosY += 1
#             if seqPosY > maxYPos:
#                 maxYPos = seqPosY
#
#             # Important: no link accross sequences
#             currIntNode = None
#
#         # print("==== Genreated instructions list")
#         # print(json.dumps(instructions, indent =2 ))
#         # print("==== Jumps to process ")
#         # print(json.dumps(jumpsToProcess, indent =2 ))
#         # print("==== Anon choices to process ")
#         # print(json.dumps(anonChoicesThatCanBeLinkedTo, indent =2 ))
#         # print("==== seqenceToNodeIntId: ")
#         # print(json.dumps(seqenceToNodeIntId, indent =2 ))
#
#         for srcInternId, sourceOutPin, targetSequennce in jumpsToProcess:
#             if targetSequennce in collapsedSequenceIdToTarget:
#                 extInt, target = collapsedSequenceIdToTarget[targetSequennce]
#                 if extInt == "INT":
#                     found = False
#                     for possibleLink, targetInternalId in anonChoicesThatCanBeLinkedTo:
#                         if target == possibleLink:
#                             internalLinks.append((srcInternId, sourceOutPin, targetInternalId))
#                             found = True
#                     if not found:
#                         if target in seqenceToNodeIntId:
#                             internalLinks.append((srcInternId, sourceOutPin, seqenceToNodeIntId[target]))
#                         else:
#                             for intLink in sequenceToMultipleIntId[target]:
#                                 internalLinks.append((srcInternId, sourceOutPin, intLink))
#                 else:
#                     externalLinks.append((srcInternId, sourceOutPin, target))
#             else:
#                 if targetSequennce == nodeId:
#                     internalLinks.append((srcInternId, sourceOutPin, nodeId))
#                 else:
#                     if targetSequennce in seqenceToNodeIntId:
#                         internalLinks.append((srcInternId, sourceOutPin, seqenceToNodeIntId[targetSequennce]))
#                     else:
#                         for intLink in sequenceToMultipleIntId[targetSequennce]:
#                             internalLinks.append((srcInternId, sourceOutPin, intLink))
#
#
#         # print("==== Internal links")
#         # print(json.dumps(internalLinks, indent =2 ))
#         # print("==== External links")
#         # print(json.dumps(externalLinks, indent =2 ))
#
#         for i, cId in enumerate(childIds):
#             if cId not in nodesReferenced:
#                 logger.debug(f"{cId} not referenced in parent sequences. Creating island node in {nodeDefnDict['id']}.")
#                 internal_id = nodeId+"_"+str(len(instructions))
#                 if cId not in allNodeIds:
#                     raise RuntimeError(f"Unknown node reference {cId}")
#                 instrDict = {"instruction_type" : "NODE_REF", "internal_id" : internal_id, "parameters" : {"id" : cId}, "external_id": cId}
#
#                 instructions.append(instrDict)
#                 instructionPos.append((0, seqPosY+1+i))
#                 seqPosY += 1
#
#         if nodeId in embedSequenceWithOutlinksTracker:
#             for srcL, srcOutPin, tarL in externalLinks:
#                 if tarL != nodeId:
#                     raise RuntimeError(f"Node {nodeId} is an embedded node but has an external reference to {tarL}. ie. node {nodeId} was referenced -* but is not the last item in the sequence it is referenced in and also has other external links")
#
#         if len(instructions) != len(instructionPos):
#             raise RuntimeError("Uneven instruction pos arr len")
#
#         _check_embedded_nodes(nodeId, nodeDefnDict["node_type"], instructions, nodeIdToDefnDict, nodeIdToParentIdDict)
#
#         resDict = { "id": nodeDefnDict["id"],
#                     "type": nodeDefnDict["node_type"],
#                     "description": nodeDefnDict["description"],
#                     "image" : nodeDefnDict["image"],
#                     "parent" : parentId,
#                     "internal_content_positions" : instructionPos,
#                     "internal_content": instructions,
#                     "internal_links": internalLinks,
#                     "external_links": externalLinks,
#                     "target_to_internal_id" : { seqId : tarIntId for seqId, tarIntId in seqenceToNodeIntId.items() if "~" not in seqId},
#                     "target_to_multiple_internal_id" : { seqId : tarList for seqId, tarList in sequenceToMultipleIntId.items()} }
#         if len(addedOnceVars) > 0:
#             logger.debug(f"Added {len(addedOnceVars)} variable for options that will only be used once")
#         return resDict, addedOnceVars
#     except Exception as e:
#         logger.warning(f"Error while processing node {nodeId}")
#         raise

def _get_hub_id(nodeDefnDict):
    hubId = f"{nodeDefnDict['id']}_Hub"
    def _hub_in_seq(seqList):
        for inst in seqList:
            instType = inst[0]
            if instType == "HUB":
                return True
        return False
    
    hasHub = _hub_in_seq(nodeDefnDict["start_sequence"])
    if hasHub:
        return hubId
    
    for seqId in nodeDefnDict["referenced_sequences"]:
        hasHub = _hub_in_seq(nodeDefnDict["referenced_sequences"][seqId])
        if hasHub:
            return hubId
    return None
    
def _get_all_nodes_with_outgoing_links_in_sequences(seqList):
    # seqList = []
    #
    # for node in nodeToDefnDict.values():
    #     seqList.append(node["start_sequence"])
    #     seqList.extend(node["referenced_sequences"].values())
    #
    # print(len(seqList))
    
    ret = []
    for seq in seqList:
        seqLen = len(seq)
        for i, seqInsr in enumerate(seq):
            if seqInsr[0] == "NODE_REF" and i < seqLen-1:
                ret.append(seqInsr[1]["id"])
    return ret

def checkInParents(referenceStr, nodeId, parentId, nodeIdToProcDict, nodeIdToChildIdsDict):
    if not parentId:
        return False
    
    if nodeId == parentId:
        return True
    
    parentNode = nodeIdToProcDict[parentId]
    if referenceStr in parentNode["target_to_internal_id"]:
        return True
    
    if referenceStr in parentNode["target_to_multiple_internal_id"]:
        return True
    
    if referenceStr in nodeIdToChildIdsDict[parentNode["id"]]:
        return True
    
    return checkInParents(referenceStr, nodeId, parentNode["parent"], nodeIdToProcDict, nodeIdToChildIdsDict)
        

def _checkExternalReferences(processNodesList, nodeIdToChildIdsDict):
    nodeIdToProcDict = {}
    for n in processNodesList:
        nodeIdToProcDict[n["id"]] = n
    
    errCnt = 0
    for n in processNodesList:
        np = n["parent"]
        for _, _, lTarget in n["external_links"]:
            valid = checkInParents(lTarget, n["id"], np, nodeIdToProcDict, nodeIdToChildIdsDict)
            if not valid:
                logger.warning(f"Unknown external reference {lTarget} in node {n['id']}")
                errCnt += 1;
    
    if errCnt > 0:
        raise RuntimeError(f"There are {errCnt} external reference errors")
    
def _getCharacterList(nodesList):
    characterSet = set()
    for n in nodesList:
        for instr in n["internal_content"]:
            if instr["instruction_type"] == "DIALOG_LINE":
                characterSet.add(instr["parameters"]["entity_name"])
    return list(characterSet)

def _getNodeIdToVariableList(nodesList, addedOnceVars):
    variableDict = {}
    varSet = set()
    for n in nodesList:
        #if n["variables"] is not None:
        variableDict[n["id"].replace("-", "_")] = n["variables"]
        
    for addedVar in addedOnceVars:
        nodeId, varNm = addedVar.split(".")
        nodeIdForm = nodeId.replace("-", "_")
        if nodeIdForm not in variableDict:
            variableDict[nodeIdForm] = []
        variableDict[nodeIdForm].append({"variable_name": varNm, "variable_default_value": False, "description": None, "variable_type": "bool"})
    #print(json.dumps(variableDict, indent=2))
    return variableDict

def _checkSetVarOk(instrLine, validVariablesSet):
    instrFixed = "\n".join([l for l in instrLine.split("\n") if not l.strip().startswith("//")])
    
    if instrFixed == "":
        return True
    
    allMatches = VAR_NM_MATCHER.findall(instrFixed)
    allMatches = [m for m in allMatches if m != "true" and m != "false"]
    if len(allMatches) == 0:
        logger.warning("No matches for variables in line")
        return False
    
    for m in allMatches:
        if m not in validVariablesSet:
            logger.warning("No match for {} in line".format(m))
            return False
        
    return True
    

def _checkCondVarOk(condLine, validVariablesSet):
    return _checkSetVarOk(condLine, validVariablesSet)

def _validateVariables(variableDict, nodesList):
    validVariablesSet = set()
    
    for vSetNm, vSetVarList in variableDict.items():
        if vSetVarList is None:
            continue
        for varDict in vSetVarList:
            t = f"{vSetNm}.{varDict['variable_name']}"
            #print(t)
            validVariablesSet.add(t)
    notOkCont = 0
    for n in nodesList:
        for instr in n["internal_content"]:
            if "condition" in instr["parameters"] and instr["parameters"]["condition"]:
                if not _checkCondVarOk(instr["parameters"]["condition"], validVariablesSet):
                    logger.warning(f"Condition '{instr['parameters']['condition']}' not ok")
                    notOkCont += 1
            if "exit_instruction" in instr["parameters"] and instr["parameters"]["exit_instruction"]:
                if not _checkSetVarOk(instr["parameters"]["exit_instruction"], validVariablesSet):
                    logger.warning(f"Exit instruction '{instr['parameters']['exit_instruction']}' not ok")
                    notOkCont += 1
                    
            if "instruction" in instr["parameters"] and instr["parameters"]["instruction"]:
                if not _checkSetVarOk(instr["parameters"]["instruction"], validVariablesSet):
                    logger.warning(f"Set instruction '{instr['parameters']['instruction']}' not ok")
                    notOkCont += 1
            
            if "eval_condition" in instr["parameters"] and instr["parameters"]["eval_condition"]:
                if not _checkCondVarOk(instr["parameters"]["eval_condition"], validVariablesSet):
                    logger.warning(f"Eval condition '{instr['parameters']['eval_condition']}' not ok")
                    notOkCont += 1
                    
    if notOkCont > 0:
        raise RuntimeError(f"There were {notOkCont} errors with logic statements")

def _parents_in_error_nodes(parentId, nodeIdToParentIdDict, errorSet):
    if parentId in errorSet:
        return True
    
    if parentId not in nodeIdToParentIdDict:
        return False
    
    return _parents_in_error_nodes(nodeIdToParentIdDict[parentId], nodeIdToParentIdDict, errorSet)


def _calc_stats(resDict):
    ret = {}
    ret["number_characters"] = len(resDict["characters"])
    
    numCutLines = 0
    numCut = 0
    numDialogLines = 0
    for n in resDict["nodes"]:
        isCut = False
        if n["type"].startswith("C-"):
            numCut += 1
            isCut = True
        for intrDict in n["internal_content"]:
            if intrDict["instruction_type"] == "DIALOG_LINE":
                if isCut:
                    numCutLines += 1
                else:
                    numDialogLines += 1
    
    ret["number_of_dialog_lines"] = numDialogLines
    ret["number_of_cutscene_lines"] = numCutLines
    ret["number_of_lines"] = numDialogLines + numCutLines
    ret["number_of_cutscene"] = numCut
    return ret

def compile_story(ast):
    nodeToDefnDict = {n["id"]: n for n in ast["nodes"]}
    #nodeToDefnDict[ast["chapter_node"]["id"]] = ast["chapter_node"]
    chapterNodeId = [n["id"] for n in ast["nodes"] if n["node_type"] == "Chapter"][0]
    logger.debug(f"Chapter node id is {chapterNodeId}")
    nodeIdToParentIdDict, nodeIdToChildIdsDict,  = build_node_hierarchy(chapterNodeId, nodeToDefnDict)
    
    # print(json.dumps(nodeIdToParentIdDict, indent=2))
    # print(json.dumps(nodeIdToChildIdsDict, indent=2))
    
    nodeIdProcessingOrder = get_processing_order(chapterNodeId, nodeIdToChildIdsDict)
    
    logger.debug(f"Nodes and their order of processing: {nodeIdProcessingOrder}")

    embedSequenceWithOutlinksTracker = set()
    
    errNodes = set()
    resDict = {"nodes" : []}
    allNodeIds = list(nodeToDefnDict.keys())
    allAddedOnceVars = []
    for nodeId in nodeIdProcessingOrder:
        parentId = nodeIdToParentIdDict[nodeId] if nodeId in nodeIdToParentIdDict else None
        childIds = nodeIdToChildIdsDict[nodeId] if nodeId in nodeIdToChildIdsDict else []
        if _parents_in_error_nodes(parentId, nodeIdToParentIdDict, errNodes):
            logger.info(f"Skipping node {nodeId} due to error in parent")
            continue
        logger.info(f"Processing internal logic of node {nodeId}")
        logger.debug(f"Parent: {parentId}, children: {childIds}")
        try:
            isEmbedded = nodeId in embedSequenceWithOutlinksTracker
            nodeDict, addedOnceVars, embeddedNodes = process_node(chapterNodeId, nodeId, parentId, childIds, isEmbedded, nodeToDefnDict, nodeIdToParentIdDict, allNodeIds)
            allAddedOnceVars.extend(addedOnceVars)
            resDict["nodes"].append(nodeDict)
            embedSequenceWithOutlinksTracker.update(set(embeddedNodes))
        except Exception as e:
            logger.exception(f"Error in node {nodeId}")
            errNodes.add(nodeId)
    
    if len(errNodes) > 0:
        raise RuntimeError(f"There are {len(errNodes)} nodes with errors. Child nodes may have been skipped")
    
    logger.info("Checking if external references are valid for all nodes")
    _checkExternalReferences(resDict["nodes"], nodeIdToChildIdsDict)
    logger.info("Checking if external references complete")
    logger.info("Getting all characters")
    resDict["characters"] = _getCharacterList(resDict["nodes"])
    resDict["characters"].sort()
    logger.info("Getting character list complete")
    logger.info("Getting variable list")
    resDict["variables"] = _getNodeIdToVariableList(ast["nodes"], allAddedOnceVars)
    logger.info("Getting variable list complete")
    _validateVariables(resDict["variables"], resDict["nodes"])
    logger.info("Validating variables complete")
    resDict["statistics"] = _calc_stats(resDict)
    logger.info("Calculating statistics complete")
    return resDict
    
    
