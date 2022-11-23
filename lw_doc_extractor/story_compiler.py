'''
Created on 13 Jul 2022

@author: Joachim Kestner
'''
import json
import collections
import re
import logging
import binascii
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
VALID_DIGITS_FOR_ID.add("#")

def _format_string(inpStr):
    inpStr = "_".join(inpStr.split())
    return ''.join(c for c in inpStr if c in VALID_DIGITS_FOR_ID)

def get_dialog_line_id(enityName, menuText, stage_directions, lineText):
    global _idToOccurenceTracker
    
    en = enityName.strip() if enityName else ""
    mt = menuText.strip() if menuText else ""
    lt = lineText.strip() if lineText else ""
    sd = stage_directions.strip() if stage_directions else ""
    
    crcStr1 = "{}#{}#{}".format(en, mt, lt)
        
    resStr = _format_string(crcStr1)
    
    acrc = binascii.crc32(crcStr1.encode("utf-8"))
    resHex = "{:08X}".format(acrc)
    
    retStr = "{}#{}".format(resHex, resStr)
    if len(retStr) > 64:
        retStr = retStr[:64]
        
    if retStr in _idToOccurenceTracker:
        num_occurances = _idToOccurenceTracker[retStr]
        newRet = retStr + "_" + str(num_occurances)
        _idToOccurenceTracker[retStr] = num_occurances + 1
        retStr = newRet
    else:
         _idToOccurenceTracker[retStr] = 1
    return  retStr

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

# rules for automatically creating a link to a hub are
#  - if last item in sequence is not a jump, choice, hub, if, shac, the_end or a node ref
#  - then if this node, in the sequence it is embedded in, is not the last instruction in the sequence, then create a return
#  - if not then link to the current nodes hub
#  - if that doesnt exist then link to the hub in the parent or if parent is subsection then to the hub of the parent of subsection
#  - if that doesnt exist raise an error
def auto_link_hub(nodeId, sequenceDict, nodeToDefnDict, nodeIdToParentIdDict, allNodesWithOutgoingLinks):
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
    
    
    for seqId in sequenceDict:
        if len(sequenceDict[seqId]) == 0:
            raise RuntimeError(f"Cannot fix sequence {seqId} as it is empty.")
        if sequenceDict[seqId][-1][0] == "THE_END":
            continue
        if sequenceDict[seqId][-1][0] not in ["CHOICE_DIALOG", "IF", "HUB", "NODE_REF", "INTERNAL_JUMP", "EXTERNAL_JUMP", "THE_END", "GENERIC_HUB"]:
            if nodeId in allNodesWithOutgoingLinks:
                sequenceDict[seqId].append(("INTERNAL_JUMP", {"referenced_id" : nodeId}))
                logger.debug(f"For sequence {seqId} adding internal return jump to {nodeId}")
            elif currentHub != None:
                sequenceDict[seqId].append(("INTERNAL_JUMP", {"referenced_id" : currentHub}))
                logger.debug(f"For sequence {seqId} adding internal jump to {currentHub}")
            elif parentHub != None:
                sequenceDict[seqId].append(("EXTERNAL_JUMP", {"referenced_id" : parentHub}))
                logger.debug(f"For sequence {seqId} adding external jump to {parentHub}")
            else:
                raise RuntimeError(f"Cannot fix sequence {seqId}. Last command of sequence {sequenceDict[seqId][-1][0]}")
    

# creates new sequences for instructions for hub, dialog choide and if and
# replaces instructions with references
def flatten_sequences(sequenceIds, nodeDefnDict):
    complexStatements = ["CHOICE_DIALOG", "IF", "HUB", "SHAC_CHOICE"]

    flatSequences = collections.OrderedDict()
    nodeId = nodeDefnDict['id']
    
    seqPos = {}
    
    hubFound = False
    
    for seqId in sequenceIds:
        if seqId == "start_sequence":
            seqToProcess = nodeDefnDict[seqId]
            seqId = f"{nodeId}_start_sequence"
        else:
            seqToProcess = nodeDefnDict["referenced_sequences"][seqId]
        if not seqId.startswith(nodeId):
            raise RuntimeError(f"Sequence {seqId} does not start with prefix of node {nodeId}")
        
        logger.debug(f"Flattenning sequence {seqId}")
        flatSequences[seqId] = []
        seqPos[seqId] = (len(seqPos), 0)
        for i, inst in enumerate(seqToProcess):
            instType = inst[0]
            complexStatementUsed = False
            if instType not in complexStatements:
                flatSequences[seqId].append(inst)
            else:
                try:
                    if complexStatementUsed:
                        raise RuntimeError(f"There con only be one complex statement within a sequence. Offending statement: {inst}")
                    if instType == "HUB":
                        if hubFound:
                            raise RuntimeError("More than one hub found in node {nodeDefnDict['id']}")
                        hubFound = True
                        if nodeDefnDict["node_type"] not in ["Chapter", "Section"]:
                            raise RuntimeError(f"Node {nodeDefnDict['id']} defines a hub but is not of type Chapter or Section")
                        
                        hubSeqId = f"{nodeDefnDict['id']}_Hub"
                        
                        flatSequences[seqId].append(("INTERNAL_JUMP", {"referenced_id" :hubSeqId}))
                        
                        flatSequences[hubSeqId] = [["HUB", {"choices" : [], "original_sequence" : seqId if i == 0 else None}]]
                        seqPos[hubSeqId] = (len(seqPos), 0)
                        
                        choices = []
                        for cCount, choice in enumerate(inst[1]):
                            choiceSeqId = f"{seqId}~{cCount}~hubchoice"
                            choices.append({"sequence_ref": choiceSeqId})
                            addInstr = ("GAME_EVENT_LISTENER", {"description": f"{choice['choice_description']}", "condition" : choice["condition"], "exit_instruction": choice["exit_instruction"], "event_id" : choice["event_id"]})
                            flatSequences[choiceSeqId] = [addInstr] + choice["sequence"]
                            seqPos[choiceSeqId] = (len(seqPos), 1)
                        flatSequences[hubSeqId][0][1]["choices"] = choices
                        
                    elif instType == "CHOICE_DIALOG":
                        choices = [dict(c) for c in inst[1]["choices"]]
                        for cCount, choice in enumerate(choices):
                            choiceSeqId = f"{seqId}~{cCount}~dialogchoice"
                            flatSequences[choiceSeqId] = choice.pop("sequence")
                            choice["sequence_ref"] = choiceSeqId    
                            seqPos[choiceSeqId] = (len(seqPos), i+1)
                        cpyDict = dict(inst[1])
                        cpyDict["choices"] = choices
                        flatSequences[seqId].append(("CHOICE_DIALOG",  cpyDict))
                    elif instType == "SHAC_CHOICE":
                        flatSequences[seqId].append(["GENERIC_HUB", {"choices" : [], "original_sequence" : None}])
                        for cCount, choice in enumerate(inst[1]):
                            choiceSeqId = f"{seqId}~{cCount}~shacchoice"
                            flatSequences[seqId][-1][1]["choices"].append({"sequence_ref": choiceSeqId})
                            addInstr = ("GAME_EVENT_LISTENER", {"description": f"{choice['choice_description']}", "condition" : None, "exit_instruction": None, "event_id" : choice["event_id"]})
                            flatSequences[choiceSeqId] = [addInstr] + choice["sequence"]
                            seqPos[choiceSeqId] = (len(seqPos), 1)
                        
                    elif instType == "IF":
                        choiceSeqIdTrue = f"{seqId}~true"
                        choiceSeqIdFalse = f"{seqId}~false"
                        flatSequences[choiceSeqIdTrue] = inst[1]["sequence_true"]
                        flatSequences[choiceSeqIdFalse] = inst[1]["sequence_false"]
                        flatSequences[seqId].append(("IF", {"eval_condition": inst[1]["eval_condition"], "sequence_ref_true" : choiceSeqIdTrue, "sequence_ref_false" :choiceSeqIdFalse}))
                        seqPos[choiceSeqIdTrue] = (len(seqPos), i+1)
                        seqPos[choiceSeqIdFalse] = (len(seqPos), i+1)
                    
                    complexStatementUsed = True
                except Exception:
                    logger.warning(f"Error occurred in sequence {seqId} while processing instruction {i}: {inst}")
                    raise
                
    return flatSequences, seqPos

def _collapse_links(sequences, allNodeIds):
    retDict = {}
    def _collapse_internal(refNode):
        seqList = sequences[refNode]
        if len(seqList) == 1:
            instType, instrPrmDict = seqList[0]
            if instType == "INTERNAL_JUMP":
                return _collapse_internal(instrPrmDict["referenced_id"])
            elif instType == "EXTERNAL_JUMP":
                return ("EXT", instrPrmDict["referenced_id"])
        return ("INT", refNode)
    
    for seqId, seqList in sequences.items():
        
        if len(seqList) == 0:
            raise RuntimeError(f"Sequence of len 0 found: {seqId}")
        
        if len(seqList) == 1:
            instType, instrPrmDict = seqList[0]
            if instType == "EXTERNAL_JUMP":
                retDict[seqId] = ("EXT", instrPrmDict["referenced_id"])
            elif instType == "INTERNAL_JUMP":
                retDict[seqId] = _collapse_internal(instrPrmDict["referenced_id"])
    return retDict

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

def _check_embeded_nodes(nodeId, nodeType, instructions, nodeIdToDefnDict, nodeIdToParentIdDict):
    for instrDict in instructions:
        if instrDict["instruction_type"] == "NODE_REF":
            refNodeId = instrDict["parameters"]["id"]
            embededType = nodeIdToDefnDict[refNodeId]["node_type"]
            
            if nodeIdToParentIdDict[refNodeId] != nodeId:
                raise RuntimeError(f"Node {refNodeId} is embeded in {nodeId}, but the parent hierarchy is incorrect. Check '_' usage")
            
            if nodeType not in _EMBED_ALLOWED_LIST:
                raise RuntimeError(f"Node {nodeId} embeds node {refNodeId}, but its of node type {nodeType} which cant embed other nodes")
            
            if nodeType == "Chapter" and embededType == "SubSection":
                raise RuntimeError(f"Chapter node {nodeId} embeds node of type SubSection {refNodeId} which is not allowed")
                
            if nodeType == "SubSection" and embededType == "SubSection":
                raise RuntimeError(f"SubSection node {nodeId} embeds node of type SubSection {refNodeId} which is not allowed")
            
            if nodeType == "SubSection" and embededType == "Section":
                raise RuntimeError(f"SubSection node {nodeId} embeds node of type Section {refNodeId} which is not allowed")

def process_node(nodeId, parentId, childIds, embedSequenceWithOutlinksTracker, nodeIdToDefnDict, nodeIdToParentIdDict, allNodeIds):
    nodeDefnDict = nodeIdToDefnDict[nodeId]
    # array to keep track of nodes that have been referenced to determine which have not
    nodesReferenced = []
    
    # print("======!!!!!!")
    # print(nodeId)
    # print(json.dumps(nodeDefnDict, indent=2))
    
    try:
    
        sequenceIds = ["start_sequence"]
        for k in nodeDefnDict["referenced_sequences"]:
            sequenceIds.append(k)
        
        flattenedSequences , sequenceStartPos = flatten_sequences(sequenceIds, nodeDefnDict)
        #print(json.dumps(flattenedSequences, indent=2))
        sequenceStartPos = {}
        
        embedSequenceWithOutlinksTracker.update(_get_all_nodes_with_outgoing_links_in_sequences(flattenedSequences.values()))
        
        # inplace
        auto_link_hub(nodeId, flattenedSequences, nodeIdToDefnDict, nodeIdToParentIdDict, embedSequenceWithOutlinksTracker)
        
        instructions = []
        instructionPos = []
        internalLinks = []
        externalLinks = []
        
        seqenceToNodeIntId = {}
        sequenceToMultipleIntId = {}
    
        collapsedSequenceIdToTarget = _collapse_links(flattenedSequences, allNodeIds)
        # print("==== Collapsed list")
        # print(json.dumps(collapsedSequenceIdToTarget, indent =2 ))
        
        currIntNode = nodeId
        
        jumpsToProcess = []
        anonChoicesThatCanBeLinkedTo = []
        
        seqPosX = 0
        seqPosY = 0
        intrPosCnt = 0
        
        maxYPos = 0
        
        # print("================= {} collaped seq".format(nodeId))
        # print(collapsedSequenceIdToTarget)
        # print("====================== collaped end")
        
        
        
        for seqId, seqList in flattenedSequences.items():
            if seqId in collapsedSequenceIdToTarget and not seqId.endswith("start_sequence"):
            #if seqId in collapsedSequenceIdToTarget:
                continue
            
            if seqId in sequenceIds:
                intrPosCnt = 0
                seqPosX = 0
            
            if seqId in sequenceStartPos:
                seqPosX, seqPosY = sequenceStartPos[seqId]
            else:
                if seqPosY > maxYPos:
                    seqPosY = maxYPos
            
            sequenceId = seqId
            shouldBeDone = False
    
            for instType, instrPrmDict in seqList:
                if shouldBeDone:
                    raise RuntimeError(f"In sequence {seqId} instruction following a jump")
                shouldBeDone = True
                
                if not _isInstrTypeAllowed(nodeId, nodeDefnDict["node_type"], seqId, instType):
                    raise RuntimeError(f"In sequence {seqId}, instruction type {instType} is not allowed within node type {nodeDefnDict['node_type']}")
                
                if instType == "INTERNAL_JUMP":
                    jumpsToProcess.append((currIntNode, 0, instrPrmDict["referenced_id"]))
                elif instType == "EXTERNAL_JUMP":
                    externalLinks.append((currIntNode, 0, instrPrmDict["referenced_id"]))
                elif instType =="CHOICE_DIALOG":
                    childIntIds = []
                    for cDict in instrPrmDict["choices"]:
                        internal_id = nodeId+"_"+str(len(instructions))
                        childIntIds.append(internal_id)
                        choiceInstrPrm = {"entity_name": instrPrmDict["entity_name"], "menu_text" : cDict["menu_text"], "spoken_text": cDict["spoken_text"], "stage_directions" : None, "condition": cDict["condition"], "exit_instruction": cDict["exit_instruction"]}
                        extCId = get_dialog_line_id(instrPrmDict["entity_name"], cDict["menu_text"], cDict["stage_directions"], cDict["spoken_text"])
                        instrDict = {"instruction_type" : "DIALOG_LINE", "internal_id" : internal_id, "parameters" : choiceInstrPrm, "external_id": extCId}
                        instructions.append(instrDict)
                        instructionPos.append((seqPosX+intrPosCnt, seqPosY))
                        sequenceStartPos[cDict["sequence_ref"]] = (seqPosX+intrPosCnt+1, seqPosY)
                        seqPosY += 1
                        if currIntNode:
                            internalLinks.append((currIntNode, 0, internal_id))
                        else:
                            anonChoicesThatCanBeLinkedTo.append((seqId, internal_id))
                        jumpsToProcess.append((internal_id, 0, cDict["sequence_ref"]))
                    intrPosCnt += 1
                    
                    if sequenceId != None:
                        sequenceToMultipleIntId[sequenceId] = childIntIds
                else:
                    intrPosAddX = 1
                    intrPosY = seqPosY
                    internal_id = nodeId+"_"+str(len(instructions))
                    instrPrms = instrPrmDict
                    extId = None
                    if instType == "IF":
                        jumpsToProcess.append((internal_id, 0, instrPrmDict["sequence_ref_true"]))
                        jumpsToProcess.append((internal_id, 1, instrPrmDict["sequence_ref_false"]))
                        instrPrms = {"eval_condition": instrPrmDict["eval_condition"]}
                        sequenceStartPos[instrPrmDict["sequence_ref_true"]] = (seqPosX+intrPosCnt+1, seqPosY)
                        seqPosY += 1
                        sequenceStartPos[instrPrmDict["sequence_ref_false"]] = (seqPosX+intrPosCnt+1, seqPosY)
                        intrPosAddX = 2
                    elif instType == "HUB":
                        for c in instrPrmDict["choices"]:
                            jumpsToProcess.append((internal_id, 0, c["sequence_ref"]))
                            sequenceStartPos[c["sequence_ref"]] = (seqPosX+intrPosCnt+1, seqPosY)
                            seqPosY += 1
                        instrPrms = {"hub_name" : f"{nodeId}_HUB"}
                        if instrPrmDict["original_sequence"]:
                            seqenceToNodeIntId[instrPrmDict["original_sequence"]] = internal_id
                        intrPosAddX = 2
                    elif instType == "GENERIC_HUB":
                        for c in instrPrmDict["choices"]:
                            jumpsToProcess.append((internal_id, 0, c["sequence_ref"]))
                            sequenceStartPos[c["sequence_ref"]] = (seqPosX+intrPosCnt+1, seqPosY)
                            seqPosY += 1
                        instrPrms = {"hub_name" : f"{internal_id}_HUB"}
                        intrPosAddX = 2
                    elif instType == "NODE_REF":
                        if instrPrmDict["id"] not in allNodeIds:
                            raise RuntimeError(f"Unknown node reference {instrPrmDict['id']}")
                        if instrPrmDict["id"] in nodesReferenced:
                            raise RuntimeError(f"Node {instrPrmDict['id']} has been reference twice")
                        
                        nodesReferenced.append(instrPrmDict["id"])
                        extId = instrPrmDict["id"]
                    elif instType == "DIALOG_LINE":
                        entNm = instrPrmDict["entity_name"]
                        entTxt = instrPrmDict["spoken_text"]
                        nmuTxt = instrPrmDict["menu_text"]
                        dsTxt = instrPrmDict["stage_directions"]
                        extId = get_dialog_line_id(entNm, nmuTxt, dsTxt, entTxt)
                    
                    instrDict = {"instruction_type" : instType, "internal_id" : internal_id, "parameters" : instrPrms, "external_id": extId}
                    instructions.append(instrDict)
                    instructionPos.append((seqPosX+intrPosCnt, intrPosY))
                    intrPosCnt += intrPosAddX
                    if currIntNode:
                        internalLinks.append((currIntNode, 0, internal_id))
                    if sequenceId:
                        seqenceToNodeIntId[sequenceId] = internal_id
                    
                    sequenceId = None
                    
                    currIntNode = internal_id
                    
                shouldBeDone = instType in ["HUB", "IF", "INTERNAL_JUMP", "EXTERNAL_JUMP", "CHOICE_DIALOG"]
            
            seqPosY += 1
            if seqPosY > maxYPos:
                maxYPos = seqPosY
            
            # Important: no link accross sequences
            currIntNode = None
            
        # print("==== Genreated instructions list")
        # print(json.dumps(instructions, indent =2 ))
        # print("==== Jumps to process ")
        # print(json.dumps(jumpsToProcess, indent =2 ))
        # print("==== Anon choices to process ")
        # print(json.dumps(anonChoicesThatCanBeLinkedTo, indent =2 ))
        # print("==== seqenceToNodeIntId: ")
        # print(json.dumps(seqenceToNodeIntId, indent =2 ))
        
        for srcInternId, sourceOutPin, targetSequennce in jumpsToProcess:
            if targetSequennce in collapsedSequenceIdToTarget:
                extInt, target = collapsedSequenceIdToTarget[targetSequennce]
                if extInt == "INT":
                    found = False
                    for possibleLink, targetInternalId in anonChoicesThatCanBeLinkedTo:
                        if target == possibleLink:
                            internalLinks.append((srcInternId, sourceOutPin, targetInternalId))
                            found = True
                    if not found:
                        if target in seqenceToNodeIntId:
                            internalLinks.append((srcInternId, sourceOutPin, seqenceToNodeIntId[target]))
                        else:
                            for intLink in sequenceToMultipleIntId[target]:
                                internalLinks.append((srcInternId, sourceOutPin, intLink))
                else:
                    externalLinks.append((srcInternId, sourceOutPin, target))
            else:
                if targetSequennce == nodeId:
                    internalLinks.append((srcInternId, sourceOutPin, nodeId))
                else:
                    if targetSequennce in seqenceToNodeIntId:
                        internalLinks.append((srcInternId, sourceOutPin, seqenceToNodeIntId[targetSequennce]))
                    else:
                        for intLink in sequenceToMultipleIntId[targetSequennce]:
                            internalLinks.append((srcInternId, sourceOutPin, intLink))
                
            
        # print("==== Internal links")
        # print(json.dumps(internalLinks, indent =2 ))
        # print("==== External links")
        # print(json.dumps(externalLinks, indent =2 ))
        
        for i, cId in enumerate(childIds):
            if cId not in nodesReferenced:
                logger.debug(f"{cId} not referenced in parent sequences. Creating island node in {nodeDefnDict['id']}.")
                internal_id = nodeId+"_"+str(len(instructions))
                if cId not in allNodeIds:
                    raise RuntimeError(f"Unknown node reference {cId}")
                instrDict = {"instruction_type" : "NODE_REF", "internal_id" : internal_id, "parameters" : {"id" : cId}, "external_id": cId}
                
                instructions.append(instrDict)
                instructionPos.append((0, seqPosY+1+i))
                seqPosY += 1
        
        if nodeId in embedSequenceWithOutlinksTracker:
            for srcL, srcOutPin, tarL in externalLinks:
                if tarL != nodeId:
                    raise RuntimeError(f"Node {nodeId} is an embeded node but has an external reference to {tarL}. ie. node {nodeId} was referenced -* but is not the last item in the sequence it is referenced in and also has other external links")
                        
        if len(instructions) != len(instructionPos):
            raise RuntimeError("Uneven instruction pos arr len")
        
        _check_embeded_nodes(nodeId, nodeDefnDict["node_type"], instructions, nodeIdToDefnDict, nodeIdToParentIdDict)
        
        resDict = { "id": nodeDefnDict["id"],
                    "type": nodeDefnDict["node_type"],
                    "description": nodeDefnDict["description"],
                    "image" : nodeDefnDict["image"],
                    "parent" : parentId,
                    "internal_content_positions" : instructionPos,
                    "internal_content": instructions,
                    "internal_links": internalLinks,
                    "external_links": externalLinks,
                    "target_to_internal_id" : { seqId : tarIntId for seqId, tarIntId in seqenceToNodeIntId.items() if "~" not in seqId},
                    "target_to_multiple_internal_id" : { seqId : tarList for seqId, tarList in sequenceToMultipleIntId.items()} }
        return resDict
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

def _getNodeIdToVariableList(nodesList):
    variableDict = {}
    varSet = set()
    for n in nodesList:
        #if n["variables"] is not None:
        variableDict[n["id"].replace("-", "_")] = n["variables"]
    #print(json.dumps(variableDict, indent=2))
    return variableDict

def _checkSetVarOk(instrLine, validVariablesSet):
    allMatches = VAR_NM_MATCHER.findall(instrLine)
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
    
    # woLinksList = _get_all_nodes_with_outgoing_links_in_sequences(nodeToDefnDict)
    # allNodesWithOutgoingLinks = set(woLinksList)

    #

    embedSequenceWithOutlinksTracker = set()
    
    errNodes = set()
    resDict = {"nodes" : []}
    allNodeIds = list(nodeToDefnDict.keys())
    for nodeId in nodeIdProcessingOrder:
        parentId = nodeIdToParentIdDict[nodeId] if nodeId in nodeIdToParentIdDict else None
        childIds = nodeIdToChildIdsDict[nodeId] if nodeId in nodeIdToChildIdsDict else []
        if _parents_in_error_nodes(parentId, nodeIdToParentIdDict, errNodes):
            logger.info(f"Skipping node {nodeId} due to error in parent")
            continue
        logger.info(f"Processing internal logic of node {nodeId}")
        logger.debug(f"Parent: {parentId}, children: {childIds}")
        try:
            nodeDict = process_node(nodeId, parentId, childIds, embedSequenceWithOutlinksTracker, nodeToDefnDict, nodeIdToParentIdDict, allNodeIds)
            resDict["nodes"].append(nodeDict)
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
    resDict["variables"] = _getNodeIdToVariableList(ast["nodes"])
    logger.info("Getting variable list complete")
    _validateVariables(resDict["variables"], resDict["nodes"])
    logger.info("Validating variables complete")
    resDict["statistics"] = _calc_stats(resDict)
    logger.info("Calculating statistics complete")
    return resDict
    
    