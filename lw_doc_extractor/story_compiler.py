'''
Created on 13 Jul 2022

@author: Joachim Kestner
'''
import json
import collections
import re
import logging

logger = logging.getLogger(__name__)

NODE_TITLE_MATCHER = re.compile("[^{]+{([^}])}")

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

# Automatically linking squences to a hub
# rules for automatically creating a link to a hub are
#  - if last item in sequence is not a jump, choice, hub, if or a node ref
#  - then link to the current nodes hub
#  - if that doesnt exist then link to the hub in the parent
#  - if that doesnt exist raise an error
def auto_link_hub(sequenceDict, currentHub, parentHub):
    for seqId in sequenceDict:
        if sequenceDict[seqId][-1][0] == "THE_END":
            continue
        if sequenceDict[seqId][-1][0] not in ["CHOICE_DIALOG", "IF", "HUB", "NODE_REF", "INTERNAL_JUMP", "EXTERNAL_JUMP"]:
            if currentHub != None:
                sequenceDict[seqId].append(("INTERNAL_JUMP", {"referenced_id" : currentHub}))
                logger.debug(f"For sequence {seqId} adding internal jump to {currentHub}")
            elif parentHub != None:
                sequenceDict[seqId].append(("EXTERNAL_JUMP", {"referenced_id" : parentHub}))
                logger.debug(f"For sequence {seqId} adding external jump to {parentHub}")
            else:
                raise RuntimeError(f"Cannot fix sequence {seqId}.")
    

# creates new sequences for instructions for hub, dialog choide and if and
# replaces instructions with references
def flatten_sequences(sequenceIds, nodeDefnDict):
    complexStatements = ["CHOICE_DIALOG", "IF", "HUB"]

    flatSequences = collections.OrderedDict()
    
    seqPos = {}
    
    hubFound = False
    
    for seqId in sequenceIds:
        if seqId == "start_sequence":
            seqToProcess = nodeDefnDict[seqId]
            seqId = f"{nodeDefnDict['id']}_start_sequence"
        else:
            seqToProcess = nodeDefnDict["referenced_sequences"][seqId]
        flatSequences[seqId] = []
        seqPos[seqId] = (len(seqPos), 0)
        for i, inst in enumerate(seqToProcess):
            instType = inst[0]
            complexStatementUsed = False
            if instType not in complexStatements:
                flatSequences[seqId].append(inst)
            else:
                if complexStatementUsed:
                    raise RuntimeError(f"There con only be one complex statement within a sequence. Offending statement: {inst}")
                if instType == "HUB":
                    if hubFound:
                        raise RuntimeError("More than one hub found in node {nodeDefnDict['id']}")
                    hubFound = True
                    if nodeDefnDict["node_type"] not in ["Chapter", "Section"]:
                        raise RuntimeError("Node {nodeDefnDict['id']} defines a hub but is not of type Chapter or Section")
                    
                    hubSeqId = f"{nodeDefnDict['id']}_Hub"
                    
                    flatSequences[seqId].append(("INTERNAL_JUMP", {"referenced_id" :hubSeqId}))
                    
                    flatSequences[hubSeqId] = [["HUB", {"choices" : []}]]
                    seqPos[hubSeqId] = (len(seqPos), 0)
                    
                    choices = []
                    for cCount, choice in enumerate(inst[1]):
                        choiceSeqId = f"{seqId}~{i}~{cCount}~hubchoice"
                        choices.append({"sequence_ref": choiceSeqId})
                        addInstr = ("GAME_EVENT_LISTENER", {"description": f"{choice['choice_description']}", "condition" : choice["condition"], "exit_instruction": choice["exit_instruction"], "event_id" : choice["event_id"]})
                        flatSequences[choiceSeqId] = [addInstr] + choice["sequence"]
                        seqPos[choiceSeqId] = (len(seqPos), 1)
                    flatSequences[hubSeqId][0][1]["choices"] = choices
                    
                elif instType == "CHOICE_DIALOG":
                    choices = [dict(c) for c in inst[1]["choices"]]
                    for cCount, choice in enumerate(choices):
                        choiceSeqId = f"{seqId}~{i}~{cCount}~dialogchoice"
                        flatSequences[choiceSeqId] = choice.pop("sequence")
                        choice["sequence_ref"] = choiceSeqId    
                        seqPos[choiceSeqId] = (len(seqPos), i+1)
                    cpyDict = dict(inst[1])
                    cpyDict["choices"] = choices
                    flatSequences[seqId].append(("CHOICE_DIALOG",  cpyDict))
                elif instType == "IF":
                    choiceSeqIdTrue = f"{seqId}~{i}~true"
                    choiceSeqIdFalse = f"{seqId}~{i}~false"
                    flatSequences[choiceSeqIdTrue] = inst[1]["sequence_true"]
                    flatSequences[choiceSeqIdFalse] = inst[1]["sequence_false"]
                    flatSequences[seqId].append(("IF", {"eval_condition": inst[1]["eval_condition"], "sequence_ref_true" : choiceSeqIdTrue, "sequence_ref_false" :choiceSeqIdFalse}))
                    seqPos[choiceSeqIdTrue] = (len(seqPos), i+1)
                    seqPos[choiceSeqIdFalse] = (len(seqPos), i+1)
                
                complexStatementUsed = True
                
    return flatSequences, seqPos

def _collapse_links(sequences):
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


def process_node(nodeDefnDict, parentId, childIds, parentHub):
    nodeId = nodeDefnDict["id"]
    
    # array to keep track of nodes that have been referenced to determine which have not
    nodesReferenced = []
    
    # print("======!!!!!!")
    # print(nodeId)
    # print(json.dumps(nodeDefnDict, indent=2))
    
    sequenceIds = ["start_sequence"]
    for k in nodeDefnDict["referenced_sequences"]:
        sequenceIds.append(k)
    
    flattenedSequences , sequenceStartPos = flatten_sequences(sequenceIds, nodeDefnDict)
    #print(json.dumps(flattenedSequences, indent=2))
    
    # inplace
    auto_link_hub(flattenedSequences, _get_hub_id(nodeDefnDict), parentHub)
    
    
    instructions = []
    internalLinks = []
    externalLinks = []
    
    seqenceToNodeIntId = {}

    collapsedSequenceIdToTarget = _collapse_links(flattenedSequences)
    # print("==== Collapsed list")
    # print(json.dumps(collapsedSequenceIdToTarget, indent =2 ))
    
    currIntNode = nodeId
    
    jumpsToProcess = []
    anonChoicesThatCanBeLinkedTo = []
    
    for seqId, seqList in flattenedSequences.items():
        
        if seqId in collapsedSequenceIdToTarget:
            continue
        
        sequenceId = seqId
        shouldBeDone = False

        for instType, instrPrmDict in seqList:
            if shouldBeDone:
                raise RuntimeError(f"In sequence {seqId} instruction following a jump")
            shouldBeDone = True
            
            if instType == "INTERNAL_JUMP":
                jumpsToProcess.append((currIntNode, instrPrmDict["referenced_id"]))
            elif instType == "EXTERNAL_JUMP":
                externalLinks.append((currIntNode, instrPrmDict["referenced_id"]))
            elif instType =="CHOICE_DIALOG":
                for cDict in instrPrmDict["choices"]:
                    internal_id = nodeId+"_"+str(len(instructions))
                    choiceInstrPrm = {"entity_name": instrPrmDict["entity_name"], "menu_text" : cDict["menu_text"], "spoken_text": cDict["spoken_text"],  "condition": cDict["condition"], "exit_instruction": cDict["exit_instruction"]}
                    instrDict = {"instruction_type" : "DIALOG_LINE", "internal_id" : internal_id, "parameters" : choiceInstrPrm, "sequence_id": None}
                    instructions.append(instrDict)
                    if currIntNode:
                        internalLinks.append((currIntNode, internal_id))
                    else:
                        anonChoicesThatCanBeLinkedTo.append((seqId, internal_id))
                    jumpsToProcess.append((internal_id, cDict["sequence_ref"]))
            else:
                internal_id = nodeId+"_"+str(len(instructions))
                instrPrms = instrPrmDict
                if instType == "IF":
                    jumpsToProcess.append((internal_id, instrPrmDict["sequence_ref_true"]))
                    jumpsToProcess.append((internal_id, instrPrmDict["sequence_ref_false"]))
                    instrPrms = {"eval_condition": instrPrmDict["eval_condition"]}
                elif instType == "HUB":
                    for c in instrPrmDict["choices"]:
                        jumpsToProcess.append((internal_id, c["sequence_ref"]))
                    instrPrms = {}
                elif instType == "NODE_REF":
                    nodesReferenced.append(instrPrmDict["id"])
                
                instrDict = {"instruction_type" : instType, "internal_id" : internal_id, "parameters" : instrPrms, "sequence_id": sequenceId}
                instructions.append(instrDict)
                if currIntNode:
                    internalLinks.append((currIntNode, internal_id))
                if sequenceId:
                    seqenceToNodeIntId[sequenceId] = internal_id
                
                sequenceId = None
                
                currIntNode = internal_id
                
            shouldBeDone = instType in ["HUB", "IF", "INTERNAL_JUMP", "EXTERNAL_JUMP", "CHOICE_DIALOG"]
        
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
    
    for srcInternId, targetSequennce in jumpsToProcess:
        if targetSequennce in collapsedSequenceIdToTarget:
            extInt, target = collapsedSequenceIdToTarget[targetSequennce]
            if extInt == "INT":
                found = False
                for possibleLink, targetInternalId in anonChoicesThatCanBeLinkedTo:
                    if target == possibleLink:
                        internalLinks.append((srcInternId, targetInternalId))
                        found = True
                if not found:
                    internalLinks.append((srcInternId, seqenceToNodeIntId[target]))
            else:
                externalLinks.append((srcInternId, target))
        else:
            internalLinks.append((srcInternId, seqenceToNodeIntId[targetSequennce]))
            
        
    # print("==== Internal links")
    # print(json.dumps(internalLinks, indent =2 ))
    # print("==== External links")
    # print(json.dumps(externalLinks, indent =2 ))
    
    for cId in childIds:
        if cId not in nodesReferenced:
            logger.debug(f"{cId} not referenced in parent sequences. Creating island node in {nodeDefnDict['id']}.")
            internal_id = nodeId+"_"+str(len(instructions))
            instrDict = {"instruction_type" : "NODE_REF", "internal_id" : internal_id, "parameters" : {"id" : cId}, "sequence_id": None}
            instructions.append(instrDict)
                    
    
    resDict = { "id": nodeDefnDict["id"],
                "type": nodeDefnDict["node_type"],
                "description": nodeDefnDict["description"],
                "image" : nodeDefnDict["image"],
                "parent" : parentId,
                "internal_content_positions" : [],
                "internal_content": instructions,
                "internal_links": internalLinks,
                "external_links": externalLinks }
    return resDict

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
    

def compile_story(ast): 
    nodeToDefnDict = {n["id"]: n for n in ast["nodes"]}
    nodeToDefnDict[ast["chapter_node"]["id"]] = ast["chapter_node"]
    nodeIdToParentIdDict, nodeIdToChildIdsDict,  = build_node_hierarchy(ast["chapter_node"]["id"], nodeToDefnDict)
    # print(json.dumps(nodeIdToParentIdDict, indent=2))
    # print(json.dumps(nodeIdToChildIdsDict, indent=2))
    
    nodeIdProcessingOrder = get_processing_order(ast["chapter_node"]["id"], nodeIdToChildIdsDict)
    
    
    resDict = {"nodes" : []}
    for nodeId in nodeIdProcessingOrder:
        parentId = nodeIdToParentIdDict[nodeId] if nodeId in nodeIdToParentIdDict else None
        childIds = nodeIdToChildIdsDict[nodeId] if nodeId in nodeIdToChildIdsDict else []
        parentHub = None
        if parentId:
            parentHub = _get_hub_id(nodeToDefnDict[parentId])
        resDict["nodes"].append(process_node(nodeToDefnDict[nodeId], parentId, childIds, parentHub))


    with open("compiler_output.json", "w") as fh:
        json.dump(resDict, fh, indent=2)
        
    return resDict
    
    