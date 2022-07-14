'''
Created on 13 Jul 2022

@author: Joachim Kestner
'''
import json
import collections
import re

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
        

# creates new sequences for instructions for hub, dialog choide and if and
# replaces instructions with references
def flatten_sequences(sequence, nodeDefnDict):
    complexStatements = ["CHOICE_DIALOG", "IF", "HUB"]

    flatSequences = collections.OrderedDict()
    
    seqPos = {}
    
    hubFound = False
    
    
    for seqId in sequences:
        if seqId == "start_sequence":
            seqToProcess = nodeDefnDict[seqId]
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
                    
                    flatSequences[seqId].append(("INTERNAL_JUMP", hubSeqId))
                    
                    flatSequences[hubSeqId] = [["HUB", []]]
                    seqPos[hubSeqId] = (len(seqPos), 0)
                    
                    choices = []
                    for cCount, choice in enumerate(inst[1]):
                        choiceSeqId = f"{seqId}~{i}~{cCount}~hubchoice"
                        choices.append({"sequence_ref": choiceSeqId})
                        addInstr = ("GAME_EVENT_LISTENER", f"{choice['choice_description']}", choice["condition"], choice["exit_instruction"])
                        flatSequences[choiceSeqId] = [addInstr] + choice["sequence"]
                        seqPos[choiceSeqId] = (len(seqPos), 1)
                    flatSequences[hubSeqId][0][1] = choices
                    
                elif instType == "CHOICE_DIALOG":
                    choices = []
                    for cCount, choice in enumerate(inst[1]["choices"]):
                        choiceSeqId = f"{seqId}~{i}~{cCount}~dialogchoice"
                        flatSequences[choiceSeqId] = choice["sequence"]
                        choices.append({"sequence_ref": choiceSeqId})
                        seqPos[choiceSeqId] = (len(seqPos), i+1)
                    flatSequences[seqId].append(("CHOICE_DIALOG", choices))
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

def process_node(nodeDefnDict, nodeIdToParentIdDict, nodeIdToChildIdsDict):
    
    print("============")
    print(nodeDefnDict["id"])
    
    sequenceIds = ["start_sequence"]
    for k in nodeDefnDict["referenced_sequences"]:
        sequenceIds.append(k)
    
    flattenedSequences , sequenceStartPos = flatten_sequences(sequenceIds, nodeDefnDict)
    # sequenceStartPos = get_flat_seq_pas(flattenedSequences)
    
    print(json.dumps(flattenedSequences, indent=2))
    
    #compile_instructions
                    
    
    resDict = { "id": nodeDefnDict["id"],
                "type": nodeDefnDict["node_type"],
                "description": nodeDefnDict["description"],
                "image" : nodeDefnDict["image"],
                "parent" : nodeIdToParentIdDict[nodeDefnDict["id"]] if nodeDefnDict["id"] in nodeIdToParentIdDict else None,
                "internal_content_positions" : [],
                "internal_content": [],
                "internal_links": [],
                "external_links": [] }
    

def compile_story(ast): 
    nodeToDefnDict = {n["id"]: n for n in ast["nodes"]}
    nodeToDefnDict[ast["chapter_node"]["id"]] = ast["chapter_node"]
    nodeIdToParentIdDict, nodeIdToChildIdsDict,  = build_node_hierarchy(ast["chapter_node"]["id"], nodeToDefnDict)
    print(json.dumps(nodeIdToParentIdDict, indent=2))
    print(json.dumps(nodeIdToChildIdsDict, indent=2))
    
    nodeIdProcessingOrder = get_processing_order(ast["chapter_node"]["id"], nodeIdToChildIdsDict)
    
    
    resDict = {"nodes" : []}
    for nodeId in nodeIdProcessingOrder:
        resDict["nodes"].append(process_node(nodeToDefnDict[nodeId], nodeIdToParentIdDict, nodeIdToChildIdsDict))

    return resDict
    
    