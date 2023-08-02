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

def get_dialog_line_file_nm_lf(enityName, menuText, lineText):
    global _idToOccurenceTracker
    
    en = enityName.strip() if enityName else ""
    mt = menuText.strip() if menuText else ""
    lt = lineText.strip() if lineText else ""
    
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
        fileNm = get_dialog_line_file_nm_lf(enityName, menuText, lineText)
    else:
        
        en = enityName.strip() if enityName else ""
        mt = menuText.strip() if menuText else ""
        lt = lineText.strip() if lineText else ""
        sd = stage_directions.strip() if stage_directions else ""
        
        if lt == "…":
            if not re.search('[a-zA-Z]{3,}', sd):
                raise RuntimeError(f"Silent dialogue line (…) needs to have a stage direction with 3 or more letters")
            fileNmWoHash = _format_string("{}_{}_{}_{}".format(chapterId, en, mt, sd), VALID_DIGITS_FOR_ID)
        else:
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
    

def detect_dup_nodes(nodeList):
    nodeNmTracker = set()
    # n["id"]: n for n
    for n in nodeList:
        if n["id"] in nodeNmTracker:
            raise RuntimeError(f"Node {n['id']} has been defined twice")
        nodeNmTracker.add(n["id"])

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

def _isInstrTypeAllowed(nodeType, instrType):
    
    allowedEverywhere = ["COMMENT", "IF", "SET", "EXTERNAL_JUMP", "INTERNAL_JUMP"]
    if instrType in allowedEverywhere:
        return True
    
    if nodeType == "C-SEG":
        return False
    
    if nodeType in ["C-CUT", "C-SAC", "C-CNM"]:
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
        return True
    
    if instrType == "HUB" and nodeType == "GameplaySection":
        return True
    
    return True

_EMBED_ALLOWED_LIST = ["Chapter", "Section", "SubSection", "GameplaySection"]

def _check_embedded_nodes_and_instructions(nodeId, nodeType, instructions, nodeIdToDefnDict, nodeIdToParentIdDict):
    for instrDict in instructions:
        instrType = instrDict["instruction_type"]
        if instrType == "NODE_REF":
            refNodeId = instrDict["parameters"]["id"]
            embeddedType = nodeIdToDefnDict[refNodeId]["node_type"]
            
            if nodeIdToParentIdDict[refNodeId] != nodeId:
                raise RuntimeError(f"Node {refNodeId} is embedded in {nodeId}, but the parent hierarchy is incorrect. Check '_' usage")
            
            if nodeType not in _EMBED_ALLOWED_LIST:
                raise RuntimeError(f"Node {nodeId} embeds node {refNodeId}, but its of node type {nodeType} which cant embed other nodes")
            
            if nodeType == "Chapter" and embeddedType in ["SubSection", "Chapter"]:
                raise RuntimeError(f"Chapter node {nodeId} embeds node of type SubSection or Chapter {refNodeId} which is not allowed")
            
            if nodeType == "Section" and embeddedType in ["Chapter", "Section"]:
                raise RuntimeError(f"Section node {nodeId} embeds node of type {embeddedType} ({refNodeId}) which is not allowed")
            
            if nodeType == "SubSection" and embeddedType in _EMBED_ALLOWED_LIST: #["Chapter", "Section", "SubSection"]:
                raise RuntimeError(f"SubSection node {nodeId} embeds node of type {embeddedType} ({refNodeId}) which is not allowed")
        
            if nodeType == "GameplaySection" and embeddedType in _EMBED_ALLOWED_LIST:
                raise RuntimeError(f"GameplaySection node {nodeId} embeds other node {refNodeId} of type {embeddedType} which is not allowed")
        if not _isInstrTypeAllowed(nodeType, instrType):
            raise RuntimeError(f"In node '{nodeId}', instruction type '{instrType}' is not allowed within node type '{nodeType}'")

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
        if instructionParameterDictionary["sequence_false"] == None:
            rawInstr = ("SET", {"instruction": "//dummy else sequence"})
            subSequencesMap[choiceSeqIdFalse] = ([rawInstr], None)
        else:
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
            try:
                extId = get_dialog_line_id(chapterNodeId, entNm, nmuTxt, dsTxt, entTxt)
            except:
                logger.warning(f"InstructionID with error: {instructionId}")
                raise
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
    logger.debug(f"Processing sequence {sequenceId}")
    
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
                if "_" not in instrPrmDict["referenced_id"] and instrPrmDict["referenced_id"] != "CONTINUE":
                    internalJumpsToProcess.append((currIntNode, 0, nodeId + "_" + instrPrmDict["referenced_id"]))
                else:
                    if not instrPrmDict["referenced_id"].startswith(chapterNodeId) and instrPrmDict["referenced_id"] != "CONTINUE":
                        raise RuntimeError(f"Jump to {instrPrmDict['referenced_id']} has an underscore in it, but does not start with the chapter id {chapterNodeId}")
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
            # if not isEmbedded:
            #     raise RuntimeError(f"Using a CONTINUE jump in a non embed node {nodeId}")
            # newLinks.append((srcInternId, sourceOutPin, nodeId))#
            
            if isEmbedded:
                newLinks.append((srcInternId, sourceOutPin, nodeId))
                logger.info(f"Bc of CONTINUE for instruction with ID '{srcInternId}' adding internal return jump to {nodeId}")
            elif parentHub != None:
                newExtLinks.append((srcInternId, sourceOutPin, parentHub))
                logger.info(f"Bc of CONTINUE for instruction with ID '{srcInternId}' adding external jump to {parentHub}")
            else:
                raise RuntimeError(f"Cannot link CONTINUE with ID '{srcInternId}'. Not embedded and no hub to link to")
            
        elif targetSequennce in sequenceIdToIntId:
            newLinks.append((srcInternId, sourceOutPin, sequenceIdToIntId[targetSequennce]))
        else:
            logger.warn(f"{targetSequennce} not found. Available internal sequences for node id {nodeId} are {sequenceIdToIntId}")
            raise RuntimeError(f"In node {nodeId} cannot create an internal link from {srcInternId} to {targetSequennce}")
        
    
    intIdWithLink = [srcIntId for srcIntId, _srcPinIdx, _tarIntId in intLinks]
    intIdWithLink.extend([srcIntId for srcIntId, _srcPinIdx, _tarSeq in newLinks])
    intIdWithLink.extend([srcIntId for srcIntId, _srcPinIdx, _tarSeq in newExtLinks])
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
    
    for refSeqNm in nodeDefnDict["referenced_sequences"]:
        if "_" in refSeqNm:
            if not refSeqNm.startswith(chapterNodeId):
                raise RuntimeError(f"Sequence {refSeqNm} has an underscore in it, but does not start with the chapter id {chapterNodeId}")
            seqNameToSeqInstrDict[refSeqNm] = nodeDefnDict["referenced_sequences"][refSeqNm]
        else:
            fixedRefSeqNm = nodeId + "_" + refSeqNm
            seqNameToSeqInstrDict[fixedRefSeqNm] = nodeDefnDict["referenced_sequences"][refSeqNm]
    
    seqNameToSeqInstrDict.update()
    
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
        
        _check_embedded_nodes_and_instructions(nodeId, nodeDefnDict["node_type"], allInstructions, nodeIdToDefnDict, nodeIdToParentIdDict)
        
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
                    "defined_external_connections" : nodeDefnDict["external_connections"]
                    }
        if len(addedOnceVars) > 0:
            logger.debug(f"Added {len(addedOnceVars)} variable for options that will only be used once")
        return resDict, allAddedOnceVars, embeddedNodes
    except Exception as e:
        logger.warning(f"Error while processing node {nodeId}")
        raise

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

def checkExtRefValidRecusive(referenceStr, nodeId, parentId, nodeIdToProcDict, nodeIdToChildIdsDict):
    if referenceStr in nodeIdToProcDict[nodeId]["defined_external_connections"]:
        return True
    
    if not parentId:
        return False
    
    if nodeId == parentId:
        return True
    
    parentNode = nodeIdToProcDict[parentId]
    if referenceStr in parentNode["target_to_internal_id"]:
        return True
    
    if referenceStr in nodeIdToChildIdsDict[parentNode["id"]]:
        return True
    
    return checkExtRefValidRecusive(referenceStr, nodeId, parentNode["parent"], nodeIdToProcDict, nodeIdToChildIdsDict)
        

def _checkExternalReferences(processNodesList, nodeIdToChildIdsDict):
    nodeIdToProcDict = {}
    for n in processNodesList:
        nodeIdToProcDict[n["id"]] = n
    
    errCnt = 0
    for n in processNodesList:
        np = n["parent"]
        for _, _, lTarget in n["external_links"]:
            valid = checkExtRefValidRecusive(lTarget, n["id"], np, nodeIdToProcDict, nodeIdToChildIdsDict)
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

def _getNodeIdToExtVariableList(rawNodesList):
    variableDict = {}
    for n in rawNodesList:
        variableDict[n["id"].replace("-", "_")] = n["external_variables"]
    return variableDict

def _getNodeIdToVariableList(rawNodesList, addedOnceVars):
    variableDict = {}
    for n in rawNodesList:
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

def _checkVarPair(variableName, variableValue, validVariablesToVarDict):
    
    if variableName not in validVariablesToVarDict:
        logger.warning("No variable definition to match given variable {}".format(variableName))
        return False
    
    varType = validVariablesToVarDict[variableName]["variable_type"]
    
    if variableValue.isdigit():
        if varType != "int":
            logger.warning(f"Types for variable {variableName} do not match. Var type is {varType}.  Used type is int")
            return False
        return True
    
    if variableValue == "true" or variableValue == "false":
        if varType != "bool":
            logger.warning(f"Types for variable {variableName} do not match. Var type is {varType}. Used type is boolean")
            return False
        return True
    
    if (variableValue.startswith("“") and variableValue.endswith("”")) or (variableValue.startswith("\"") and variableValue.endswith("\"")):
        if varType != "string":
            logger.warning(f"Types for variable {variableName} do not match. Var type is {varType}. Used type is string")
            return False
        stringValToSet = variableValue[1:-1]
        if stringValToSet not in validVariablesToVarDict[variableName]["validation"]["is_one_of"]:
            logger.warning(f"For string variable {variableName} trying to use invalid string value {stringValToSet}")
            return False
        return True
    
    if variableValue in validVariablesToVarDict:
        #logger.warning(f"Setting and comparing variables not supprted for var {variableName} and {variableValue}")
        return validVariablesToVarDict[variableValue]["variable_type"] == varType
    
    logger.warning(f"Cannot confirm matching types between {variableName} and {variableValue}")
    return False

def _checkSetVarOk(instrLine, validVariablesToVarDict):
    instrFixed = "\n".join([l for l in instrLine.split("\n") if not l.strip().startswith("//")])
    
    if instrFixed == "":
        return True
    
    if instrFixed.count("=") != 1:
        logger.warning("Set variable instruction has more or less than 1 equal: "+instrFixed)
        return False
    
    varNm, varValToSet = [s.strip() for s in instrFixed.split("=")]
    
    arithmaticOps = ["+", "-", "/", "*", "%"]
    
    otherValsToSet = [varValToSet]
    for aOp in arithmaticOps:
        newList = []
        for ov in otherValsToSet:
            newVals = [n.strip() for n in ov.split(aOp)]
            newList.extend(newVals)
        otherValsToSet = newList
        
    if varNm in validVariablesToVarDict and validVariablesToVarDict[varNm]["variable_type"] == "string" and len(otherValsToSet) != 1:
        logger.warning(f"Set string variable instruction can only be set to a fixed string for variable {varNm}")
        return False
    
    for otherVal in otherValsToSet:
        if not _checkVarPair(varNm, otherVal, validVariablesToVarDict):
            return False
    return True
    # allMatches = VAR_NM_MATCHER.findall(instrFixed)
    # allMatches = [m for m in allMatches if m != "true" and m != "false"]
    # if len(allMatches) == 0:
    #     logger.warning("No matches for variables in line")
    #     return False
    #
    # for m in allMatches:
    #     if m not in validVariablesSet:
    #         logger.warning("No match for {} in line".format(m))
    #         return False
    #
    # return True
    

def _checkCondVarOk(condLine, validVariablesToVarDict):
    instrFixed = "\n".join([l for l in condLine.split("\n") if not l.strip().startswith("//")])
    
    if instrFixed == "":
        return True
    
    compOp = ["==", "!=", "<=",">=", "<", ">"]
    
    andList = condLine.split("||")
    for andpair in andList:
        varpairs = andpair.split("&&")
        for varpair in varpairs:
            totCount = 0
            
            usedOp = None
            for op in compOp:
                oc = varpair.count(op)
                if oc > 0:
                    totCount += oc
                    usedOp = op
            
            if totCount != 1:
                logger.warning(f"Found {varpair.count('==')} '==' for a var pair in condition : "+instrFixed)
                return False
            varNm, varValToComp = [s.strip() for s in varpair.split(usedOp)]
            if varValToComp in validVariablesToVarDict:
                varT = varNm
                varNm = varValToComp
                varValToComp = varT
            
            if not _checkVarPair(varNm, varValToComp, validVariablesToVarDict):
                #logger.warning(f"In condition comparison between pair {varNm} and {varValToComp} not valid: Condition was '{instrFixed}'")
                return False
    return True

def _validateVariables(variableDict, nodesList, externalVariableDict):
    validVariablesToVarDict = {}
    #print(json.dumps(variableDict, indent=2))
    
    for vSetNm, vSetVarList in externalVariableDict.items():
        if vSetVarList is None:
            continue
        for extVar in vSetVarList:
            validVariablesToVarDict[extVar] = {"variable_type" : "bool"}
    
    for vSetNm, vSetVarList in variableDict.items():
        if vSetVarList is None:
            continue
        for varDict in vSetVarList:
            t = f"{vSetNm}.{varDict['variable_name']}"
            #print(t)
            validVariablesToVarDict[t] = varDict
    notOkCont = 0
    for n in nodesList:
        for instr in n["internal_content"]:
            if "condition" in instr["parameters"] and instr["parameters"]["condition"]:
                if not _checkCondVarOk(instr["parameters"]["condition"], validVariablesToVarDict):
                    logger.warning(f"Condition '{instr['parameters']['condition']}' not ok")
                    notOkCont += 1
            if "exit_instruction" in instr["parameters"] and instr["parameters"]["exit_instruction"]:
                if not _checkSetVarOk(instr["parameters"]["exit_instruction"], validVariablesToVarDict):
                    logger.warning(f"Exit instruction '{instr['parameters']['exit_instruction']}' not ok")
                    notOkCont += 1
                    
            if "instruction" in instr["parameters"] and instr["parameters"]["instruction"]:
                if not _checkSetVarOk(instr["parameters"]["instruction"], validVariablesToVarDict):
                    logger.warning(f"Set instruction '{instr['parameters']['instruction']}' not ok")
                    notOkCont += 1
            
            if "eval_condition" in instr["parameters"] and instr["parameters"]["eval_condition"]:
                if not _checkCondVarOk(instr["parameters"]["eval_condition"], validVariablesToVarDict):
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
    detect_dup_nodes(ast["nodes"])
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
    _validateVariables(resDict["variables"], resDict["nodes"], _getNodeIdToExtVariableList(ast["nodes"]))
    logger.info("Validating variables complete")
    resDict["statistics"] = _calc_stats(resDict)
    logger.info("Calculating statistics complete")
    return resDict
    