'''
Created on 19 Jul 2022

@author: joachim
'''


#
# C:\tmp\rt\2022-05-25>"C:\Program Files\IronPython 2.7\ipy.exe" test.py
# C:\git\lw-doc-extractor\test_files> "C:\Program Files\IronPython 2.7\ipy.exe" ..\lw_doc_extractor\resources\articy_populator.py  comp_out.json --auth_file mycred

import pdb
import sys, os, glob
import inspect
import json
import argparse

import logging
import uuid

__author__ = 'Joachim Kestner <kestner@lightword.de>'
__version__ = "0.1"

logger = logging.getLogger(__name__)
articyLogger = logging.getLogger("ArticyApi")
articyLogger.setLevel("WARNING")

try:
    import clr
    from System import Func, Delegate, Guid
except:
    logger.exception("Error importing .net dependencies of articy populator")


pathsToAdd = [r"C:\soft\articy_draft_API\bin\x64", r"C:\soft\articy_draft_API\bin\x64\SharpSVN_1_9", r"C:\soft\articy_draft_API\bin\x64\SharpSVN_1_8", r"C:\soft\articy_draft_API\bin\x64\SharpSVN_1_7", r"C:\soft\articy_draft_API\bin\x64\en-US"]

origDir= os.getcwd()
for p in pathsToAdd:
    sys.path.append(p)
    os.chdir(p)
    for f in glob.glob("*.dll"):
        try:
            clr.AddReference(f)
        except:
            print("Could not import "+p+"\\"+f)
    os.chdir(origDir)

try:
    from  Articy.Api import ArticyApi
    import Articy
except:
    logger.exception("Error importing dependencies of articy populator")


class MyOpenProjArgs(Articy.Api.OpenProjectArgs):
    def __init__(self, ProjGuid):
        self.ProjGuid = ProjGuid
        self.ProjectGuid = ProjGuid
        self.ProjectFolder = r"C:\work\articy_projects\api_test_proj_cli"
        self.CleanCheckout = True
        self.ForceProjectFolder = True
        self.ScmUsername = "Kestner"
        self.ScmPassword = "coqjanjaasioqweDE"
        self.OpenExclusively = False


# string aMessageSource, EntryType aType, string aText
class MyLogger:
    def mylog(*args, **kwargs):
        msgStr = "{} {} {}".format(args[1], str(args[2]).split(".")[-1], args[3])
        if str(args[2]) == "Trace" or str(args[2]) == "Debug":
            articyLogger.debug(msgStr) 
        elif str(args[2]) == "Info":
            articyLogger.info(msgStr)
        else:
            articyLogger.warning(msgStr)
            
class ArticyApiWrapper:
    
    def __init__(self, session):
        self.session = session
        self.int_char_dict = {n.upper(): obj for n, obj in self.get_character_name_to_obj_dict().items()}
        logger.info("Entities: {}".format(self.int_char_dict))

    def create_flow_fragment(self, parentObj, dispName, template=None):
        logger.debug("Creating flow fragment {} with template {}".format(dispName, template))
        return self.session.CreateFlowFragment( parentObj, dispName, template)
    
    def create_dialog(self, parentObj, dispName, template=None):
        logger.debug("Creating dialog {} with template {}".format(dispName, template))
        return self.session.CreateDialogue( parentObj, dispName, template)
        
    def create_dialog_fragment(self, parentObj, text, template=None, speaker=None):
        diagFrag = self.session.CreateDialogueFragment( parentObj, text, template)
        if speaker:
            if speaker.upper() not in self.int_char_dict:
                logger.warning("Articy object for speaker {} not found".format(speaker))
            else:
                diagFrag["Speaker"] = self.int_char_dict[speaker.upper()]
        return diagFrag
    
    def create_instruction(self, parentObj, instructionText, template=None):
        logger.debug("Creating instruction {} with template {}".format(instructionText, template))
        return self.session.CreateInstruction( parentObj, instructionText, template)
    
    def create_condition(self, parentObj, conditionText, template=None):
        logger.debug("Creating condition {} with template {}".format(conditionText, template))
        return self.session.CreateCondition(parentObj, conditionText, template)
    
    def create_hub(self, parentObj, dispName, template=None):
        logger.debug("Creating hub {} with template {}".format(dispName, template))
        return self.session.CreateHub(parentObj, dispName, template)
        
    def create_connection(self, srcObj, targetObj, sourceOutputPinIndex=0):
        srcOuputPins = srcObj.GetOutputPins()
        targetInpPins = targetObj.GetInputPins()
        
        if not srcOuputPins:
            raise RuntimeError("srcOuputPins is None or empty")
        if not targetInpPins:
            raise RuntimeError("targetInpPins is None or empty")
        #logger.debug("Connecting pins of {} and {}".format(srcObj.GetTechnicalName(), targetObj.GetTechnicalName()))
        retObj = self.session.ConnectPins(srcOuputPins[sourceOutputPinIndex], targetInpPins[0])
        
        return retObj
        
    def create_internal_connection(self, srcParentObj, targetObj):
        srcInputPins = srcParentObj.GetInputPins()
        targetInpPins = targetObj.GetInputPins()
        
        if not srcInputPins:
            raise RuntimeError("srcInputPins is None or empty")
        if not targetInpPins:
            raise RuntimeError("targetInpPins is None or empty")
        logger.debug("Connecting internal pins of {} and {}".format(srcParentObj.GetTechnicalName(), targetObj.GetTechnicalName()))
        retObj = self.session.ConnectPins(srcInputPins[0], targetInpPins[0])
        return retObj
    
    def create_internal_return_connection(self, srcObj, targetParentObj, parentObjOutputPinIndex=0):
        srcOutputPins = srcObj.GetOutputPins()
        outPins = targetParentObj.GetOutputPins()
        
        if not srcOutputPins:
            raise RuntimeError("srcOutputPins is None or empty")
        if not outPins:
            raise RuntimeError("outPins is None or empty")
        logger.debug("Connecting to return pin of {}:{} from {}".format(targetParentObj.GetTechnicalName(), parentObjOutputPinIndex, srcObj.GetTechnicalName()))
        retObj = self.session.ConnectPins(srcOutputPins[0], outPins[parentObjOutputPinIndex])
        return retObj
    
    def SetPinExpressions(self, nodeObj, condition=None, instruction=None):
        iPins = nodeObj.GetInputPins()
        oPins = nodeObj.GetOutputPins()
        
        if condition:
            if len(iPins) != 1:
                raise RuntimeError("Cannot set pin condition. More than 1 pin")
            else:
                iPins["Expression"] = condition.strip()
        if instruction:
            if len(oPins) != 1:
                raise RuntimeError("Cannot set pin instruction. More than 1 pin")
            else:
                oPins["Expression"] = condition.strip()
    
    def _get_char_int(self, entitiesFolder):
        res = {}
        for c in entitiesFolder.GetChildren():
            #['AddAttachmentToStrip', 'AddInputPin', 'AddOutputPin', 'CanBePartitioned', 'CanHaveAttachments', 'CanHaveChildren', 'ClearStrip', 'Equals', 'FindIndex', 'GetAllowedChildrenTypes', 'GetAttachments', 'GetAvailableProperties', 'GetChildren', 'GetColor', 'GetColumnIndex', 'GetDataType', 'GetDisplayName', 'GetExternalId', 'GetFlowPosition', 'GetFlowSize', 'GetHashCode', 'GetInputPin', 'GetInputPins', 'GetObjectContext', 'GetObjectUrl', 'GetOutputPin', 'GetOutputPins', 'GetParent', 'GetPartitionId', 'GetPreviewImage', 'GetPropertyInfo', 'GetShortId', 'GetStripElements', 'GetStripIds', 'GetStripMap', 'GetTechnicalName', 'GetTemplateId', 'GetTemplateTechnicalName', 'GetText', 'GetType', 'HasColor', 'HasDisplayName', 'HasExternalId', 'HasPreviewImage', 'HasProperty', 'HasShortId', 'HasTechnicalName', 'HasText', 'HoldsPartition', 'Id', 'InsertAttachmentIntoStrip', 'IsConnectable', 'IsCustomizeable', 'IsDisplayNameCalculated', 'IsFolder', 'IsInContext', 'IsInDocumentContext', 'IsInFlowContext', 'IsInLocationContext', 'IsReadOnly', 'IsSystemFolder', 'IsUserFolder', 'IsValid', 'IsValidExpressoScript', 'Item', 'MayAddAttachmentToStrip', 'MayInsertAttachmentIntoStrip', 'MaySetObjectReference', 'MemberwiseClone', 'ObjectType', 'ReferenceEquals', 'RemoveAttachmentFromStrip', 'RemoveAttachmentFromStripAtIndex', 'RemoveInputPin', 'RemoveOutputPin', 'RunQuery', 'SetColor', 'SetDisplayName', 'SetExternalId', 'SetFlowPosition', 'SetFlowSize', 'SetPreviewImage', 'SetShortId', 'SetTechnicalName', 'SetTemplate', 'SetText', 'ToString', 'TypeName', 'ValidateExpressoScript', '__class__', '__delattr__', '__doc__', '__eq__', '__format__', '__getattribute__', '__getitem__', '__hash__', '__init__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__setitem__', '__sizeof__', '__str__', '__subclasshook__']
            if c.IsFolder:
                res.update(self._get_char_int(c))
            else:
                res[str(c.GetDisplayName())] = c
        return res
        
    def get_character_name_to_obj_dict(self):
        entFolder = self.session.GetSystemFolder(Articy.Api.SystemFolderNames.Entities)
        return self._get_char_int(entFolder)


def _eval_parser_log_arguments(args):
    msgFormat='%(asctime)s %(name)s %(levelname)s:  %(message)s'
    #msgFormat="{asctime} {levelname}:  {message}"
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format=msgFormat, style="{")
    elif args.extra_verbose:
        logging.basicConfig(level=logging.DEBUG, format=msgFormat, style="{")
    else:
        logging.basicConfig(level=logging.WARN, format=msgFormat, style="{")
        
def getNodeTmpl(node):
    typeMap = { "Chapter" : "Chapter",
                "Section" : "Section",
                "D-EAV" : "D_EAV",
                "D-DEF" : "D_DEF",
                "C-CUT" : "C_CUT",
                "C-SEG" : "C_SEG"
                }
    if node["type"] not in typeMap:
        raise RuntimeError("Invalid node type {}".format(node["type"]))
    return typeMap[node["type"]]

def create_instruction(articyApi, parentNodeId, flowFragmentObj, instruction, posX, posY):
    logger.debug("In {} creating instruction {}".format(parentNodeId, instruction))
    eventIdInTitle = ["STAGE_EVENT", "SYNC_STAGE_EVENT", "GAME_EVENT_LISTENER", "LOAD_STAGE"]
    generic  = ["START_QUEST",  "END_QUEST", "THE_END"] + eventIdInTitle
    
    # templateMap = { "START_QUEST" : "StartQuest",
    #                 "END_QUEST" : "EndQuest",
    #                 "STAGE_EVENT" : "StageEvent",
    #                 "SYNC_STAGE_EVENT" : "StageEvent",
    #                 "GAME_EVENT_LISTENER" : "GameEventListener",
    #                 "THE_END" : "TheEnd",
    #                 "LOAD_STAGE" : "LoadStage"
    #     }
    
    # TODO: if
    
    def get_tmpl_nm(instrType):
        # res = ""
        # for part in instrType.split("_"):
        #     res += part[:1].upper() + part[1:].lower()
        return instrType
    
    instrType = instruction["instruction_type"]
    instrPrm = instruction["parameters"]
    
    if instrType in generic:
        if instrType in eventIdInTitle:
            if "event_id" in instrPrm:
                refId = instrPrm["event_id"]
            else:
                refId = "{}:{}_{}".format(parentNodeId, "_".join(instrType.split("_")[:2]), "_".join(instrPrm["description"].split(" ")))
        elif instrType.endswith("_QUEST"):
            refId = instrPrm["quest_id"]
        else:
            if instrPrm["description"] is None:
                refId = "{}:{}".format(parentNodeId, str(uuid.uuid4())[:8])
            else:
                refId = "{}:{}".format(parentNodeId, "_".join(instrPrm["description"].split(" ")))
        articyObj = articyApi.create_flow_fragment(flowFragmentObj, refId, template=get_tmpl_nm(instrType))
        articyObj["Text"] =  instrPrm["description"] if "description" in instrPrm and instrPrm["description"] else ""
    
    elif instrType == "DIALOG_LINE":
        articyObj = articyApi.create_dialog_fragment(flowFragmentObj, instrPrm["spoken_text"], template=None, speaker=instrPrm["entity_name"])
    elif instrType == "SET":
        articyObj = articyApi.create_instruction(flowFragmentObj, instrPrm["instruction"])
    elif instrType == "HUB":
        articyObj = articyApi.create_hub(flowFragmentObj, instrPrm["hub_name"])
    elif instrType == "IF":
        articyObj = articyApi.create_condition(flowFragmentObj, instrPrm["eval_condition"])
    else:
        raise RuntimeError("Unexpected instruction type {}".format(instrType))
    
    return articyObj

def get_mapped_position(posX, posY):
    return posX*400, posY*400

def create_internal_links(articyApi, flowFragmentObj, internalIdToLinkObjects, internal_links):
    pass

def create_external_links(articyApi, flowFragmentObj, nodeIdToInternalIdToLinkObjects, external_links):
    pass

def create_node_internals(articyApi, parentNodeId, flowFragmentObject, nodeDict, nodeIdToNodeDefn):
    internalIdToArticyObj = {}
    nodeIdToObject = {}
    
    if nodeDict["description"]:
        flowFragmentObject.SetText(nodeDict["description"])
    
    for i, instr in enumerate(nodeDict["internal_content"]):
        articyObj = None
        posX, posY = nodeDict["internal_content_positions"][i]
        if instr["instruction_type"] == "NODE_REF":
            print(instr)
            refId = instr["parameters"]["id"]
            refNode = nodeIdToNodeDefn[refId]
            if refNode["type"].startswith("D-"):
                articyObj = articyApi.create_dialog(flowFragmentObject, refId, template=getNodeTmpl(refNode))
            else:
                articyObj = articyApi.create_flow_fragment(flowFragmentObject, refId, template=getNodeTmpl(refNode))
            nodeIdToObject[instr["parameters"]["id"]] = articyObj
            
        else:
            articyObj = create_instruction(articyApi, parentNodeId, flowFragmentObject, instr, posX, posY)
        internalIdToArticyObj[instr["internal_id"]] = articyObj
        articyObj.SetFlowPosition(*get_mapped_position(posX, posY))
        if instr["sequence_id"]:
            articyObj.SetExternalId(instr["sequence_id"])
            
    for int_link in nodeDict["internal_links"]:
        print(int_link)
        linkSrc,  linkTarget = int_link
        if linkSrc == linkTarget:
            raise RuntimeError("Can create link {}".format(int_link))
        if linkSrc == parentNodeId:
            articyApi.create_internal_connection(flowFragmentObject, internalIdToArticyObj[linkTarget])
        elif linkTarget == parentNodeId:
            articyApi.create_internal_return_connection(internalIdToArticyObj[linkSrc], flowFragmentObject)
        else:
            articyApi.create_connection(internalIdToArticyObj[linkSrc], internalIdToArticyObj[linkTarget])
    return internalIdToArticyObj, nodeIdToObject


def create_nodes_internals(articyApi, flowFragmentObj, nodesList):
    nodeIdToInternalIdToArticyObj = {}
    globalNodeIdToObject = {}
    
    nodeIdToNodeDefn = {}
    for node in nodesList:
        nodeIdToNodeDefn[node["id"]] = node
    
    for node in nodesList:
        
        nodeId = node["id"]
        if node["type"] == "Chapter":
            articyObj = articyApi.create_flow_fragment(flowFragmentObj, nodeId, template="Chapter")
            globalNodeIdToObject[nodeId] = articyObj
        else:
            articyObj = globalNodeIdToObject[nodeId]
            
        internalIdToArticyObj, nodeIdToObject = create_node_internals(articyApi, nodeId, articyObj, node, nodeIdToNodeDefn)
        nodeIdToInternalIdToArticyObj[nodeId] = internalIdToArticyObj
        
        ddList = [n for n in nodeIdToObject if n in globalNodeIdToObject]
        if len(ddList):
            raise RuntimeError("Following node(s) was defined twice: {}".format(ddList))
        else:
            globalNodeIdToObject.update(nodeIdToObject)
            
    
        
            
    
    

def main():
    parser = argparse.ArgumentParser(description=__doc__+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("intput_file", help="The input json file")
    parser.add_argument("--server", default="server0185.articy.com", help="Server URL")
    parser.add_argument("--server_port", type=int, default=13170, help="Server Port")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable info logging")
    parser.add_argument("-vv", "--extra_verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--auth_file", help="File with username on first line and password on second line")
    
    
    args = parser.parse_args()
    _eval_parser_log_arguments(args)
    
    projectToOpenName = "api_test_proj"

    ml = MyLogger();
    ArticyApi.Startup(ml.mylog)
    
    session = ArticyApi.CreateSession()

    session.ConnectToServer(args.server, args.server_port)
    
    if args.auth_file:
        with open(args.auth_file) as fh:
            lines = fh.readlines()
        user, userpass = lines[0].strip(), lines[1].strip()
    else:
        user = input("Enter your articy username:").strip()
        userpass = input("Enter your articy password:").strip()
    #print("'{}' '{}'".format( user, userpass))
    session.Login(user, userpass)
    
    try:
        if not session.IsLoggedIn():
            logger.warning("Session is not logged in")
        else:
            logger.info("Login complete")
        
        projList = session.GetProjectList()
        
        logger.debug("Searching for project")
        projToOpen = None
        for proj in projList:
            logger.debug("Project {}: {}".format(proj.DisplayName, proj.Id))
            if(proj.DisplayName == projectToOpenName):
                projToOpen = proj.Id
        
        
        if(projToOpen):
            logger.debug("Found project to open: {}".format(projToOpen))
            opArts = MyOpenProjArgs(projToOpen)
            
            #pdb.set_trace()
            
            with open(args.intput_file) as fh:
                sourceObj = json.load(fh)
            
            session.OpenProject(opArts)
            logger.info("Project {} opened".format(projectToOpenName))
            
            articyApi = ArticyApiWrapper(session)
            
            sysFolder = session.GetSystemFolder(Articy.Api.SystemFolderNames.Flow)
            
            session.ClaimPartition( sysFolder.GetPartitionId() )
            f1 = articyApi.create_flow_fragment(sysFolder, "Top new flow fragment" )
            
            # inpPins = f1.GetInputPins()
            # inpPins[0]["Expression"] = "true == true"
            # outPins = f1.GetOutputPins()
            # outPins[0]["Expression"] = "false == false"
            # print(inpPins[0].GetAvailableProperties())
            
            create_nodes_internals(articyApi, f1, sourceObj["nodes"])
            
            
            # characterDict = get_character_name_to_obj_dict(session)
            # logger.info("Character list: {}".format(characterDict.keys()))
            
    finally:
        session.UnclaimAllMyPartitions()
        session.Logout()
        ArticyApi.Shutdown()
    print("Done")

if __name__ == "__main__":
    main()
