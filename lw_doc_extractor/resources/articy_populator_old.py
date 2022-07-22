# '''
# Created on 19 Jul 2022
#
# @author: joachim
# '''
#
#
# #
# # C:\tmp\rt\2022-05-25>"C:\Program Files\IronPython 2.7\ipy.exe" test.py
# #
#
# import pdb
# import clr, sys, os, glob
# import inspect
# import json
#
# import logging
# logging.basicConfig(level=logging.DEBUG)
#
# logger = logging.getLogger(__name__)
# articyLogger = logging.getLogger("ArticyApi")
# articyLogger.setLevel("WARNING")
#
# from System import Func, Delegate, Guid
#
# pathsToAdd = [r"C:\soft\articy_draft_API\bin\x64", r"C:\soft\articy_draft_API\bin\x64\SharpSVN_1_9", r"C:\soft\articy_draft_API\bin\x64\SharpSVN_1_8", r"C:\soft\articy_draft_API\bin\x64\SharpSVN_1_7", r"C:\soft\articy_draft_API\bin\x64\en-US"]
#
# origDir= os.getcwd()
# for p in pathsToAdd:
#     sys.path.append(p)
#     os.chdir(p)
#     for f in glob.glob("*.dll"):
#         try:
#             clr.AddReference(f)
#         except:
#             print("Could not import "+p+"\\"+f)
#     os.chdir(origDir)
#
# from  Articy.Api import ArticyApi
# import Articy
#
#
# class MyOpenProjArgs(Articy.Api.OpenProjectArgs):
#     def __init__(self, ProjGuid):
#         self.ProjGuid = ProjGuid
#         self.ProjectGuid = ProjGuid
#         self.ProjectFolder = r"C:\work\articy_projects\api_test_proj_cli"
#         self.CleanCheckout = True
#         self.ForceProjectFolder = True
#         self.ScmUsername = "Kestner"
#         self.ScmPassword = "coqjanjaasioqweDE"
#         self.OpenExclusively = False
#
#
# # string aMessageSource, EntryType aType, string aText
# class MyLogger:
#     def mylog(*args, **kwargs):
#         msgStr = "{} {} {}".format(args[1], str(args[2]).split(".")[-1], args[3])
#         if str(args[2]) == "Trace" or str(args[2]) == "Debug":
#             articyLogger.debug(msgStr) 
#         elif str(args[2]) == "Info":
#             articyLogger.info(msgStr)
#         else:
#             articyLogger.warning(msgStr) 
#
# def create_flow_fragment(session, parentObj, dispName, template=None):
#     return session.CreateFlowFragment( parentObj, dispName, template)
#
# def create_dialog(session, parentObj, dispName, template=None):
#     return session.CreateDialogue( parentObj, dispName, template)
#
# def create_dialog_fragment(session, parentObj, text, template=None):
#     return session.CreateDialogueFragment( parentObj, text, template)
#
# def create_connection(session, srcObj, targetObj, sourceOutputPinIndex=0):
#     srcOuputPins = srcObj.GetOutputPins()
#     targetInpPins = targetObj.GetInputPins()
#
#     if not srcOuputPins:
#         raise RuntimeError("srcOuputPins is None or empty")
#     if not targetInpPins:
#         raise RuntimeError("targetInpPins is None or empty")
#     #logger.debug("Connecting pins of {} and {}".format(srcObj.GetTechnicalName(), targetObj.GetTechnicalName()))
#     retObj = session.ConnectPins(srcOuputPins[sourceOutputPinIndex], targetInpPins[0])
#
#     return retObj
#
# def create_internal_connection(session, srcParentObj, targetObj):
#     srcInputPins = srcParentObj.GetInputPins()
#     targetInpPins = targetObj.GetInputPins()
#
#     if not srcInputPins:
#         raise RuntimeError("srcInputPins is None or empty")
#     if not targetInpPins:
#         raise RuntimeError("targetInpPins is None or empty")
#     logger.debug("Connecting internal pins of {} and {}".format(srcParentObj.GetTechnicalName(), targetObj.GetTechnicalName()))
#     retObj = session.ConnectPins(srcInputPins[0], targetInpPins[0])
#     return retObj
#
# def create_internal_return_connection(session, srcObj, targetParentObj, parentObjOutputPinIndex=0):
#     srcOutputPins = srcObj.GetOutputPins()
#     outPins = targetParentObj.GetOutputPins()
#
#     if not srcOutputPins:
#         raise RuntimeError("srcOutputPins is None or empty")
#     if not outPins:
#         raise RuntimeError("outPins is None or empty")
#     logger.debug("Connecting to return pin of {}:{} from {}".format(targetParentObj.GetTechnicalName(), parentObjOutputPinIndex, srcObj.GetTechnicalName()))
#     retObj = session.ConnectPins(srcOutputPins[0], outPins[parentObjOutputPinIndex])
#     return retObj
#
# def process_nodes(session, characterDict, parentObj, nodes):
#     nodeIdToNodesObjDict = {}
#
#     ext_links_to_create = set()
#     logger.info("Processing {} nodes".format(len(nodes)))
#     for i, node in enumerate(nodes):
#         logger.info("Processing node {}".format(node["id"]))
#         if node["type"] == "dialog":
#             nodeObj = create_dialog(session, parentObj, node["id"], template="FixedDefaultDialog")
#             logger.info("Created dialog {}: {} ({})".format( node["id"], nodeObj.GetTechnicalName(), nodeObj["Id"]))
#         else:
#             nodeObj = create_flow_fragment(session, parentObj, node["id"])
#             logger.info("Created flow fragment {}: {} ({})".format( node["id"], nodeObj.GetTechnicalName(), nodeObj["Id"]))
#
#         nodeObj.SetFlowPosition(i*200.0, i*420.0)
#         if node["description"]:
#             nodeObj["Text"] = node["description"]
#         nodeIdToNodesObjDict[node["id"]] = nodeObj
#
#         allCharactersUsed = {}
#
#         for j, int_node in enumerate(node["internal_content"]):
#             if int_node["type"] == "dialog_line":
#                 diaFragObj = create_dialog_fragment(session, nodeObj, int_node["line"], template=None)
#                 diaFragObj.SetFlowPosition(j*150.0, j*450.0)
#                 logger.info("Created dialog fragment {}: {} ({})".format( int_node["id"], diaFragObj.GetTechnicalName(), diaFragObj["Id"]))
#                 nodeIdToNodesObjDict[int_node["id"]] = diaFragObj
#                 try:
#                     speakerObj = characterDict[int_node["character"]]
#                     diaFragObj["Speaker"] = speakerObj
#                     allCharactersUsed[int_node["character"]] = speakerObj
#                     #diaFragObj.SetDisplayName(int_node["character"])
#                     #print(dir(diaFragObj))
#                     #print(diaFragObj.GetStripMap("Speaker"))
#                     #print(diaFragObj.GetAvailableProperties())
#                     #diaFragObj.AddAttachmentToStrip("Speaker", speakerObj) 
#                     #raise RuntimeError("end")
#
#                 except KeyError:
#                     logger.warning("Unable to get entity for character {}".format(int_node["character"]))
#
#         for c in allCharactersUsed:
#             nodeObj.AddAttachmentToStrip( "attachments", allCharactersUsed[c] );
#
#         # create internal links
#         for int_linkFrom, intLinkTo in node["internal_links"]:
#             if int_linkFrom == node["id"]:
#                 create_internal_connection(session, nodeIdToNodesObjDict[int_linkFrom], nodeIdToNodesObjDict[intLinkTo])
#                 logger.info("Created internal link {} ({}) -> {} ({})".format( int_linkFrom, nodeIdToNodesObjDict[int_linkFrom].GetTechnicalName(), intLinkTo, nodeIdToNodesObjDict[intLinkTo].GetTechnicalName()))
#             else:
#                 create_connection(session, nodeIdToNodesObjDict[int_linkFrom], nodeIdToNodesObjDict[intLinkTo])
#                 logger.info("Created link {} ({}) -> {} ({})".format( int_linkFrom, nodeIdToNodesObjDict[int_linkFrom].GetTechnicalName(), intLinkTo, nodeIdToNodesObjDict[intLinkTo].GetTechnicalName()))
#
#         allExternal = True
#         for origin, target in node["external_links"]:
#             if origin != node["id"]:
#                 allExternal = False
#
#         extTargetSet = set()
#         extToPinDict = {}
#         for origin, target in node["external_links"]:
#
#             if allExternal:
#                 extTargetSet.add((node["id"], 0, target))
#             elif target not in extToPinDict:
#                 if len(extToPinDict) > 0:
#                     nodeObj.AddOutputPin()
#                 extToPinDict[target] = len(extToPinDict)
#
#                 if origin != node["id"]:
#                     create_internal_return_connection(session, nodeIdToNodesObjDict[origin], nodeObj, extToPinDict[target])
#
#                 extTargetSet.add((node["id"], extToPinDict[target], target))
#
#         for t in extTargetSet:
#             ext_links_to_create.add(t)
#             logger.info("Added {}:{} -> {} external link to be created".format(*t))
#
#     logger.info("Creating external links")
#     for srcId, srcPinOutId, tarId in ext_links_to_create:
#         if tarId.startswith("A") or tarId.startswith("B") or tarId.startswith("C") or tarId.startswith("D"):
#             create_connection(session, nodeIdToNodesObjDict[srcId], nodeIdToNodesObjDict[tarId], srcPinOutId)
#             logger.info("Created external link {} ({}):{} -> {} ({})".format(srcId, nodeIdToNodesObjDict[srcId].GetTechnicalName(), srcPinOutId, tarId, nodeIdToNodesObjDict[tarId]))
#
#
# def _get_char_int(sesion, entitiesFolder):
#     res = {}
#     for c in entitiesFolder.GetChildren():
#         #['AddAttachmentToStrip', 'AddInputPin', 'AddOutputPin', 'CanBePartitioned', 'CanHaveAttachments', 'CanHaveChildren', 'ClearStrip', 'Equals', 'FindIndex', 'GetAllowedChildrenTypes', 'GetAttachments', 'GetAvailableProperties', 'GetChildren', 'GetColor', 'GetColumnIndex', 'GetDataType', 'GetDisplayName', 'GetExternalId', 'GetFlowPosition', 'GetFlowSize', 'GetHashCode', 'GetInputPin', 'GetInputPins', 'GetObjectContext', 'GetObjectUrl', 'GetOutputPin', 'GetOutputPins', 'GetParent', 'GetPartitionId', 'GetPreviewImage', 'GetPropertyInfo', 'GetShortId', 'GetStripElements', 'GetStripIds', 'GetStripMap', 'GetTechnicalName', 'GetTemplateId', 'GetTemplateTechnicalName', 'GetText', 'GetType', 'HasColor', 'HasDisplayName', 'HasExternalId', 'HasPreviewImage', 'HasProperty', 'HasShortId', 'HasTechnicalName', 'HasText', 'HoldsPartition', 'Id', 'InsertAttachmentIntoStrip', 'IsConnectable', 'IsCustomizeable', 'IsDisplayNameCalculated', 'IsFolder', 'IsInContext', 'IsInDocumentContext', 'IsInFlowContext', 'IsInLocationContext', 'IsReadOnly', 'IsSystemFolder', 'IsUserFolder', 'IsValid', 'IsValidExpressoScript', 'Item', 'MayAddAttachmentToStrip', 'MayInsertAttachmentIntoStrip', 'MaySetObjectReference', 'MemberwiseClone', 'ObjectType', 'ReferenceEquals', 'RemoveAttachmentFromStrip', 'RemoveAttachmentFromStripAtIndex', 'RemoveInputPin', 'RemoveOutputPin', 'RunQuery', 'SetColor', 'SetDisplayName', 'SetExternalId', 'SetFlowPosition', 'SetFlowSize', 'SetPreviewImage', 'SetShortId', 'SetTechnicalName', 'SetTemplate', 'SetText', 'ToString', 'TypeName', 'ValidateExpressoScript', '__class__', '__delattr__', '__doc__', '__eq__', '__format__', '__getattribute__', '__getitem__', '__hash__', '__init__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__setitem__', '__sizeof__', '__str__', '__subclasshook__']
#         if c.IsFolder:
#             res.update(_get_char_int(sesion, c))
#         else:
#             res[str(c.GetDisplayName())] = c
#     return res
#
# def get_character_name_to_obj_dict(session):
#     entFolder = session.GetSystemFolder(Articy.Api.SystemFolderNames.Entities)
#     return _get_char_int(session, entFolder)
#
# def main():
#     projectToOpenName = "api_test_proj"
#
#     ml = MyLogger();
#     ArticyApi.Startup(ml.mylog)
#
#     session = ArticyApi.CreateSession()
#
#     session.ConnectToServer("server0185.articy.com", 13170)
#     session.Login("Kestner", "coqjanjaasioqweDE")
#
#
#     try:
#         if not session.IsLoggedIn():
#             logger.warning("Session is not logged in")
#         else:
#             logger.info("Login complete")
#
#         projList = session.GetProjectList()
#
#         logger.debug("Searching for project")
#         projToOpen = None
#         for proj in projList:
#             logger.debug("Project {}: {}".format(proj.DisplayName, proj.Id))
#             if(proj.DisplayName == projectToOpenName):
#                 projToOpen = proj.Id
#
#
#         if(projToOpen):
#             logger.debug("Found project to open: {}".format(projToOpen))
#             opArts = MyOpenProjArgs(projToOpen)
#
#             #pdb.set_trace()
#
#             with open("out.json") as fh:
#                 sourceObj = json.load(fh)
#
#             session.OpenProject(opArts)
#             logger.info("Project {} opened".format(projectToOpenName))
#
#             sysFolder = session.GetSystemFolder(Articy.Api.SystemFolderNames.Flow)
#             characterDict = get_character_name_to_obj_dict(session)
#             logger.info("Character list: {}".format(characterDict.keys()))
#
#             # session.ClaimPartition( sysFolder.GetPartitionId() )
#             # f1 = create_flow_fragment(session, sysFolder, "Top flow fragment" )
#             # process_nodes(session, characterDict, f1, sourceObj["nodes"])
#
#
#     finally:
#         session.UnclaimAllMyPartitions()
#         session.Logout()
#         ArticyApi.Shutdown()
#     print("Done")
#
# if __name__ == "__main__":
#     main()
