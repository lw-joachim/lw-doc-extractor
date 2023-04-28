"""
Extract and process data produced by the story compiler
"""

import argparse
import os
import logging
import k3logging
import sys
import subprocess

from lw_doc_extractor import __version__, gspeech_synthesis
from lw_doc_extractor.main import cli
import errno
import json
from argparse import RawDescriptionHelpFormatter, ArgumentDefaultsHelpFormatter
import random
import time
import collections
import csv
import tempfile
import shutil
import datetime

__author__ = 'Joachim Kestner <kestner@lightword.de>'

logger = logging.getLogger(__name__)

def get_node_to_types(compOutDict):
    #"is_cutscene" : n["type"].startswith("C-")
    return {n["id"] : n["type"]  for n in compOutDict["nodes"]}
    
def get_node_to_description(compOutDict):
    #"is_cutscene" : n["type"].startswith("C-")
    return {n["id"] : n["description"]  for n in compOutDict["nodes"]}

def get_chapter_id(compOutDict):
    for n in compOutDict["nodes"]:
        if n["type"] == "Chapter":
            return n["id"]
        
    raise RuntimeError("No chapter node in commpiler output")
            
def _mkdir_ignore_exists(dirPath):
    try:
        os.makedirs(dirPath)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def _clear_files(dirPath, ignoreList=[]):
    numDeleted = 0
    for filename in os.listdir(dirPath):
        if filename in ignoreList:
            continue
        file_path = os.path.join(dirPath, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
    logger.info(f"From {dirPath} deleted {numDeleted} paths")
            
def get_all_lines(compOutDict, filterEmpty=False):
    retLines = []
    for n in compOutDict["nodes"]:
        for intrDict in n["internal_content"]:
            if intrDict["instruction_type"] == "DIALOG_LINE":
                diaLineDict = {"id" : intrDict["external_id"],
                               "parent_node_id" : n["id"],
                               "speaker" : intrDict["parameters"]["entity_name"],
                               "text" : intrDict["parameters"]["spoken_text"],
                               "stage_directions" : intrDict["parameters"]["stage_directions"],
                               "line_attributes" : intrDict["parameters"]["line_attributes"]}
                for k, v in diaLineDict.items():
                    if k != "stage_directions" and k != "text":
                        if v == None:
                            raise RuntimeError(f"A line has a null value for {k} which is not allowed. Line id: {diaLineDict['id']}, parent node id: {diaLineDict['parent_node_id']}")
                retLines.append(diaLineDict)
    logger.debug(f"Found {len(retLines)} lines")
    if filterEmpty:
        retLines = [l for l in retLines if l["text"] is not None]
        logger.debug(f"After filtering there remained {len(retLines)} lines")
    return retLines

# def get_all_lines_excl_empty(compOutDict):
#     retLines = []
#     errCnt = 0
#     for n in compOutDict["nodes"]:
#         for intrDict in n["internal_content"]:
#             if intrDict["instruction_type"] == "DIALOG_LINE":
#                 diaLineDict = {"id" : intrDict["external_id"],
#                                "parent_node_id" : n["id"],
#                                "speaker" : intrDict["parameters"]["entity_name"],
#                                "text" : intrDict["parameters"]["spoken_text"],
#                                "stage_directions" : intrDict["parameters"]["stage_directions"],
#                                "line_attributes" : intrDict["parameters"]["line_attributes"]}
#                 for k, v in diaLineDict.items():
#                     if k == "stage_directions":
#                         continue
#                     elif k == "text":
#                         if v == None:
#                             logger.info(f"Line does not contain any spoken text. Ignoring. ID {intrDict['external_id']}")
#                             break
#                     elif v == None:
#                         logger.error(f"A line has a null value for {k} which is not allowed. Line id: {diaLineDict['id']}, parent node id: {diaLineDict['parent_node_id']}")
#                         errCnt += 1
#                 else:
#                     retLines.append(diaLineDict)
#     if errCnt > 0:
#         raise RuntimeError(f"Encountered errors on {errCnt} lines")
#     return retLines

def extract_dialog_lines_cli():
    parser = argparse.ArgumentParser(description="Extract lines from compiler output."+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("input_file", help="The compiler output json file")
    parser.add_argument("output_file", help="The output json file")
    k3logging.set_parser_log_arguments(parser)

    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
    with open(args.input_file) as fh:
        compOutDict = json.load(fh)
        
    with open(args.output_file, "w") as fh:
        lineDicts = get_all_lines(compOutDict, filterEmpty=True)
        json.dump(lineDicts, fh, indent=2)
        logger.info(f"Writing lines to {args.output_file}")
    logger.info(f"Final output written to {args.output_file}")
    
def generate_audio_recording_files(compilerOutput, outputDir):
    
    nodeIdToTypeMap = get_node_to_types(compilerOutput)
    nodeIdToDescrMap = get_node_to_description(compilerOutput)
    lineDictList = get_all_lines(compilerOutput, filterEmpty=True)
    
    linesForMasterCsv = []
    nodeToLines = collections.OrderedDict()
    
    nodeToCharacters = {}
    
    speakerSet = set()
    
    nodeToSpeakerSet = {}
    
    for lineDict in lineDictList:
        speaker = lineDict["speaker"]
        node = lineDict["parent_node_id"]
        
        if node not in nodeToLines:
            nodeToLines[node] = []
        nodeToLines[node].append(lineDict)
        
        if node not in nodeToSpeakerSet:
            nodeToSpeakerSet[node] = set()
        nodeToSpeakerSet[node].add(speaker)
        
        speakerSet.add(speaker)

    speakerList = sorted(list(speakerSet))
    
    def _write_line(lineEntry, fhMinmal, fhFull, surrSpeaker, lineDict):
        pass
    
    def _write_both(fhMinmal, fhFull, prefixStr, txtToWrite):
        fhMinmal.write(prefixStr+txtToWrite)
        fhFull.write(prefixStr+txtToWrite)
        
    def _write_on_full_only(_fhMinmal, fhFull, prefixStr, txtToWrite):
        fhFull.write(prefixStr+txtToWrite)
    
    
    with open(os.path.join(outputDir, 'audio_line_referece.csv'), 'w', newline='') as csvfile:
    
        fieldnames = ['speaker', 'parent_node_id', "text", "id"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, dialect='excel',  extrasaction='ignore')
        writer.writeheader()
    
        for sp in speakerList:
            targetPath = os.path.join(outputDir, f"{sp}_lines_for_recording.txt")
            targetComplPath = os.path.join(outputDir, f"{sp}_lines_for_recording_with_others.txt")
            fhMinimal = open(targetPath, "w", encoding="utf-8")
            fhFull = open(targetComplPath, "w", encoding="utf-8")
            
            _write_both(fhMinimal, fhFull, "", f"Lines for audio recoding for character {sp}\n")
            
            ct = 0
            for node in nodeToLines:
                if sp not in nodeToSpeakerSet[node]:
                    continue
                
                titleStr = nodeIdToTypeMap[node] + " "+ node
                _write_both(fhMinimal, fhFull, "", "\n\n"+ titleStr + "\n" + "="*len(titleStr) +"\n")
                if nodeIdToDescrMap[node]:
                    _write_both(fhMinimal, fhFull, "", nodeIdToDescrMap[node] + "\n" + "-"*len(titleStr) +"\n")
                
                _write_both(fhMinimal, fhFull, "", "\n")
                
                for lineDict in nodeToLines[node]:
                    speaker = lineDict["speaker"]
                    writeFunction  = _write_on_full_only
                    prefixInd = " "*16
                    prefixIndInclSpeaker = prefixInd + f"{speaker}: "
                    if sp == speaker:
                        prefixInd = ""
                        prefixIndInclSpeaker = ""
                        writeFunction = _write_both
                        writer.writerow(lineDict)
                        
                    if lineDict["stage_directions"]:
                        writeFunction(fhMinimal, fhFull, prefixInd, "(" + lineDict["stage_directions"] + ")\n")
                    writeFunction(fhMinimal, fhFull, prefixIndInclSpeaker, lineDict["text"] + "\n")
                    writeFunction(fhMinimal, fhFull, "", "\n")
                    
                    ct += 1

            fhMinimal.close()
            fhFull.close()
            
            logger.info(f"Written {ct} lines for speaker {sp}.")
            
    logger.info(f"Finished writing audio recoding script files for {len(speakerList)} characters.")
            
def generate_audio_recording_files_cli():
    parser = argparse.ArgumentParser(description="Generate scripts for audio recordings."+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__))
    parser.add_argument("input_file", help="The compiler output json file")
    parser.add_argument("output_directory", help="The output directory to which the generated files are written to.")

    k3logging.set_parser_log_arguments(parser)

    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)    
    
    try:
        os.makedirs(args.output_directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
        
    with open(args.input_file) as fh:
        compOutDict = json.load(fh)
        
    generate_audio_recording_files(compOutDict, args.output_directory)


def update_audio_files(lineDictList, outputDirectory, authFile):
    allResultFilesToDict={lineDict["id"]+".wav" : lineDict for lineDict in lineDictList}
    _clear_files(outputDirectory, ignoreList=list(allResultFilesToDict.keys()))
    alreadyExistingFiles = []
    for filename in os.listdir(outputDirectory):
        if filename in allResultFilesToDict:
            alreadyExistingFiles.append(filename)
    
    lineDictsToGenerate = [allResultFilesToDict[f] for f in allResultFilesToDict if f not in alreadyExistingFiles]
    
    #gspeech_synthesis.set_google_application_credentials_global(authFile)
    speechGenClient = gspeech_synthesis.GTextToSpeechClient(authFile)
    random.seed(3)
    speakerToVoiceMap = {
        "MAJOR_DOMO" : ("en-US-Neural2-A", 1.0, 0.0),
        "DOORMAN" : ("en-US-Neural2-A", 1.0, 0.0),
        "HEZION" : ("en-IN-Wavenet-C", 1.0, 0.0),
        "NARRATOR" : ("en-GB-Neural2-D", 1.0, 0.0),
        "ZADOK" : ("en-GB-Wavenet-D", 1.0, 0.0),
        "BEN" : ("en-GB-Neural2-B", 1.0, 0.0),
        "AARON" : ("en-US-Neural2-A", 1.0, 0.0),
        "JESUS" : ("en-GB-Neural2-D", 1.0, 0.0),
        "ADA" : ("en-GB-Neural2-A", 1.0, 0.0),
        "JOHANNA" : ("en-AU-Neural2-A", 1.0, 0.0)
        }
    
    restList = [
             "en-AU-Wavenet-B",
             "en-AU-Wavenet-D", 
             "en-AU-Neural2-D",
             "en-GB-Wavenet-B",
             "en-GB-Wavenet-D",
             "en-US-Neural2-A",
             ]
    
    maleCharacters = {}
    
    mappedSpeakerToVoiceMap = {}
    
    if not os.path.isdir(outputDirectory):
        raise RuntimeError(f"Invalid output directory {outputDirectory}")
    numLines = len(lineDictsToGenerate)
    logger.info(f"Generating audio files for {numLines} audio lines")
    for i, lineDict in enumerate(lineDictsToGenerate):
        fileNm = lineDict["id"]+".wav"
        if fileNm in alreadyExistingFiles:
            continue
        if i % 20 == 0 and i != 0:
            logger.info(f"Generated {i} audio files out of {numLines}")
        outfile = os.path.join(outputDirectory, fileNm)
        if lineDict["speaker"] in speakerToVoiceMap:
            voice, speed, pitch = speakerToVoiceMap[lineDict["speaker"]]
        elif lineDict["speaker"] in mappedSpeakerToVoiceMap:
            voice, speed, pitch = mappedSpeakerToVoiceMap[lineDict["speaker"]]
        else:
            voice = restList[random.randint(0, len(restList)-1)]
            speed = 1.0 # random.uniform(1, 1)
            pitch = random.uniform(-5.0, 5.0)
            mappedSpeakerToVoiceMap[lineDict["speaker"]] = voice, speed, pitch
        
        speechGenClient.synthesize_speech(lineDict["text"], outfile, voice, speed, pitch)
        time.sleep(0.4)
        
    logger.info(f"Finished generating {numLines} audio files")
        

def update_audio_files_cli():
    parser = argparse.ArgumentParser(description="Generate audio files for given lines. "+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("input_file", help="The lines json file")
    parser.add_argument("--auth_file", required=True, help="The google server credentials file")
    parser.add_argument("ouput_directory", help="The output directory")
    
    k3logging.set_parser_log_arguments(parser)

    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
    
    try:
        os.makedirs(args.ouput_directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    
    with open(args.input_file) as fh:
        lineDictList = json.load(fh)
    
    update_audio_files(lineDictList, args.ouput_directory, args.auth_file)
    
    logger.info(f"Final output written to {args.ouput_directory}")
    
def update_story_chapter(scriptInputFile, projectDirectory, googleAuthFile, articyConfigPath, dryRun, workingDir, updateAudioFiles):
    
    if not scriptInputFile.endswith(".docx") or not os.path.isfile(scriptInputFile):
        raise RuntimeError(f"Input file is not a valid docx file: {scriptInputFile}")
    
    with open(articyConfigPath) as fh:
        articyConfig = json.load(fh)
        
    tmpDir = workingDir
    logger.info(f"Working in temporary directory {tmpDir}")
    tmpCompOutFile = os.path.join(tmpDir, "compiler_output.json")
    tmpRawOutFile = os.path.join(tmpDir, "raw.txt")
    tmpDebug = os.path.join(tmpDir, "debug")
    os.makedirs(tmpDebug)
    cli.run_main(scriptInputFile, tmpCompOutFile, tmpRawOutFile, None, tmpDebug)
    
    with open(tmpCompOutFile) as fh:
        compOutDict = json.load(fh)
    
    chapterId = get_chapter_id(compOutDict)
    
    if dryRun:
        targetStoryDir = os.path.join(tmpDir, "Story", "Chapters", chapterId)
    else:
        targetStoryDir = os.path.join(projectDirectory, "Story", "Chapters", chapterId)
    
    genFilesDir    = os.path.join(targetStoryDir, "GeneratedFiles")
    scriptDir      = os.path.join(targetStoryDir, "Script")
    audioDir       = os.path.join(targetStoryDir, "Audio")
    audioScriptDir = os.path.join(audioDir, "GeneratedScriptsForAudioRecording")
    genAudioDir    = os.path.join(audioDir, "GeneratedVoicelines")
    recAudioDir    = os.path.join(audioDir, "RecordedVoicelines")
    
    _mkdir_ignore_exists(genFilesDir)
    _mkdir_ignore_exists(scriptDir)
    _mkdir_ignore_exists(audioScriptDir)
    _mkdir_ignore_exists(genAudioDir)
    _mkdir_ignore_exists(recAudioDir)
    
    _clear_files(genFilesDir)
    _clear_files(scriptDir)
    _clear_files(audioScriptDir)
    
    shutil.copy(tmpCompOutFile, os.path.join(genFilesDir, "compiler_output.json"))
    
    shutil.copy(scriptInputFile, os.path.join(scriptDir, f"{chapterId}.docx"))
    shutil.copy(tmpRawOutFile, os.path.join(scriptDir, f"{chapterId}_raw.txt"))
    
    targetProject = articyConfig["test_project"] if dryRun else articyConfig["project"]
    
    authFile = os.path.join(tmpDir, "authfile")
    
    with open(authFile, "w") as fh:
        fh.write("{}\n{}".format(articyConfig["user"], articyConfig["password"]))
    
    #cli.run_populator(tmpCompOutFile, targetProject, "One", "-v", articyConfig["iron_python"], articyConfig["server_host"], articyConfig["server_port"], authFile, articyConfig["articy_api_lib"])

    generate_audio_recording_files(compOutDict, audioScriptDir)

    if updateAudioFiles:
        update_audio_files(get_all_lines(compOutDict, filterEmpty=True), genAudioDir, googleAuthFile)
        
    logger.info("Update story chapter process complete")
    
def update_story_chapter_cli():
    parser = argparse.ArgumentParser(description="Update story chapter in project. "+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("input_file", help="The input document file")
    parser.add_argument("project_directory", help="The directory of the project")
    parser.add_argument("--gauth", required=True, help="The google server json credentials file. Required.")
    parser.add_argument("--articy-config", required=True, help="Json file containing the the articy configuration. Parameter is required. Required keys are:\ntest_project, project: the test and production articy projects\nuser, password: the articy username and pass\nserver_host, server_port: articy server host and port\niron_python: iron python exe path\narticy_api_lib: path to the articy api")
    parser.add_argument("--dry-run", action="store_true", help="If flag is set project directory will not be changed and import will happen into a test directory and test articy project")
    parser.add_argument("--dry-run-dir", help="A directory that can be specified that will be used instead of a temporary directory for debugging. Only can be used in combination with dry-run")
    parser.add_argument("--dry-run-audio", action="store_true", help="Force generating audio in a dry run. Only can be used in combination with dry-run-dir")
    
    k3logging.set_parser_log_arguments(parser)

    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
    
    genrateAudio = False if args.dry_run else True
    if args.dry_run and args.dry_run_dir:
        tmpDir = args.dry_run_dir
        if args.dry_run_audio:
            genrateAudio = True
    else:
        tmpDirHandle = tempfile.TemporaryDirectory()
        tmpDir = tmpDirHandle.name
    
    update_story_chapter(args.input_file, args.project_directory, args.gauth, args.articy_config, args.dry_run, tmpDir, genrateAudio)

def get_all_lines_for_chapter(projectDirectory, chapterId, filterEmpty=False):
    
    compOutpath = os.path.join(projectDirectory, "Story", "Chapters", chapterId, "GeneratedFiles", "compiler_output.json")
    with open(compOutpath) as fh:
        compOutDict = json.load(fh)
        
    return get_all_lines(compOutDict, filterEmpty)

def get_line_audio_state_for_chapter(projectDirectory, chapterId):
    allChLines = get_all_lines_for_chapter(projectDirectory, chapterId, filterEmpty=True )
    
    allLineIdSet = set([l["id"] for l in allChLines])
    
    
    audioDir = os.path.join(projectDirectory, "Story", "Chapters", chapterId, "Audio")
    genAudioDir    = os.path.join(audioDir, "GeneratedVoicelines")
    recAudioDir    = os.path.join(audioDir, "RecordedVoicelines")
    
    allRecoredMap = {}
    allGeneratedMap = {}
    extraGeneratedPathList = []
    extraRecordedPathList = []
        
    for tAudioId, tAudioFile in [(os.path.splitext(f)[0], f) for f in os.listdir(genAudioDir) if f.endswith(".wav")]:
        if tAudioId in allLineIdSet:
            allGeneratedMap[tAudioId] = os.path.join(genAudioDir, tAudioFile)
        else:
            extraGeneratedPathList.append(tAudioFile)
            
    for dirpath, _dirnames, filenames in os.walk(recAudioDir):
        for tAudioId, tAudioFile in [(os.path.splitext(f)[0], f) for f in filenames if f.endswith(".wav")]:
            if tAudioId in allLineIdSet:
                allRecoredMap[tAudioId] = os.path.join(dirpath, tAudioFile)
            else:
                extraRecordedPathList.append(tAudioFile)

    id_to_audio = collections.OrderedDict()
    missingRecordedList = []
    missingIdList = []
    for aId in allLineIdSet:
        if aId in allRecoredMap:
            id_to_audio[aId] = allRecoredMap[aId]
        elif aId in allGeneratedMap:
            id_to_audio[aId] = allGeneratedMap[aId]
            missingRecordedList.append(aId)
        else:
            missingRecordedList.append(aId)
            missingIdList.append(aId)
            
    retDict = {
        "id_to_audio" : id_to_audio,
        "id_to_generated" : allGeneratedMap,
        "id_to_recorded" : allRecoredMap,
        "missing_recorded" : missingRecordedList,
        "missing_ids": missingIdList,
        "extra_generated" : extraGeneratedPathList,
        "extra_recorded" : extraRecordedPathList
        }
    
    return retDict

def get_audio_bank_data_for_complete_project(projectDirectory):
    
    completeBankMap = collections.OrderedDict()
    audioErrReport = {}
    audioBankStateReport = {}
    audioErrReportKeys = ["missing_recorded", "extra_recorded", "missing_ids", "extra_generated"]
    
    for aChapter in ["LF"]: # os.listdir(chaptersDir):
        lineAudioState = get_line_audio_state_for_chapter(projectDirectory, aChapter)
        completeBankMap.update(lineAudioState["id_to_audio"])
        
        audioBankStateReport[aChapter] = {k: len(lineAudioState[k]) for k in lineAudioState}
        # sumJson = json.dumps(audioBankStateReport[aChapter])
        # logger.info(f"{sumJson}")
        audioErrReport[aChapter] = { k: lineAudioState[k] for k in audioErrReportKeys}
    
    return completeBankMap, audioErrReport, audioBankStateReport

def validate_create_audio_bank_for_complete_project(projectDirectory, targetDirectory=None, reportDirectory=None):
    completeBankMap, audioErrReport, audioBankStateReport = get_audio_bank_data_for_complete_project(projectDirectory)
    logger.info("Completed extracting project audio state")
    for chId in audioBankStateReport:
        logger.info(f"Audio info for chapter {chId}:\n{json.dumps(audioBankStateReport[chId], indent=2)}")
        
    if targetDirectory:
        for lineId in completeBankMap:
            shutil.copy(completeBankMap[lineId], targetDirectory)
        
        logger.info(f"Copied {len(completeBankMap)} files to {targetDirectory}")
    
    if reportDirectory:
        repPrefix = str(datetime.datetime.now().replace(microsecond=0).isoformat()).replace(":", "_")
        with open(os.path.join(reportDirectory, repPrefix+"_audio_state_summary.json"), "w") as fh:
            json.dump(audioBankStateReport, fh, indent=2)
        with open(os.path.join(reportDirectory, repPrefix+"_audio_errors.json"), "w") as fh:
            json.dump(audioErrReport, fh, indent=2)
        logger.info(f"Wrote 2 report files to {reportDirectory}")
        
def audio_bank_for_complete_project_cli():
    parser = argparse.ArgumentParser(description="Check and optinally export audio bank. "+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__))
    parser.add_argument("project_directory", help="The directory of the project")
    parser.add_argument("-a", "--audio_dir", help="The directory to export the audio bank to")
    parser.add_argument("-r", "--report_dir", help="the directory to write the reports to")
    
    k3logging.set_parser_log_arguments(parser)
    args = parser.parse_args()
    k3logging.eval_parser_log_arguments(args)
    
    validate_create_audio_bank_for_complete_project(args.project_directory, args.audio_dir, args.report_dir)
    
def get_sorted_audio_ids_by_emotion(lineDicts):
    emotionToLineIdMap = {}
    for lineDict in lineDicts:
        if "emotion" in lineDict["line_attributes"]:
            emotionVal = lineDict["line_attributes"]["emotion"]
            if emotionVal not in emotionToLineIdMap:
                emotionToLineIdMap[emotionVal] = []
            
            emotionToLineIdMap[emotionVal].append(lineDict["id"])
        else:
            if "default" not in emotionToLineIdMap:
                emotionToLineIdMap["default"] = []
            emotionToLineIdMap["default"].append(lineDict["id"])
    return emotionToLineIdMap

def sort_audio_files_by_emotion(compilerOutputFilePath, inputAudioDir, targetDirectory):
    with open(compilerOutputFilePath) as fh:
        compOutDict = json.load(fh)
    
    lineDicts = get_all_lines(compOutDict, filterEmpty=True)
    emotionToFileMap = get_sorted_audio_ids_by_emotion(lineDicts)
            
    logger.info(f"Found the following emotions: {emotionToFileMap.keys()}")
            
    for em in sorted(emotionToFileMap.keys()):
        emTarDir = os.path.join(targetDirectory, em)
        
        os.mkdir(emTarDir)
        
        for lineId in emotionToFileMap[em]:
            
            fileNm = f"{lineId}.wav"
            srcFilePath = os.path.join(inputAudioDir, fileNm)
            
            if not os.path.isfile(srcFilePath):
                raise RuntimeError(f"Missing audio file {srcFilePath}")
            
            tarFilePath = os.path.join(emTarDir, fileNm)
            tarFilePath = tarFilePath.replace("#", "_")
            shutil.copy(srcFilePath, tarFilePath)
            logger.debug(f"Copied {srcFilePath} to {tarFilePath}")
            
        logger.info(f"Copied {len(emotionToFileMap[em])} audio files for emotion {em}")
        
    logger.info("Completed grouping audio files by emotion")
    

def sort_audio_files_by_emotion_cli():
    parser = argparse.ArgumentParser(description="Sort audio files into folders by their emotion. "+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("input_file", help="The compiler output json file")
    parser.add_argument("input_audio_dir", help="The input directory with all audio files")
    parser.add_argument("target_output_dir", help="The output directory into which the sorted files will be placed. Needs to be empty")
    
    k3logging.set_parser_log_arguments(parser)

    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
    sort_audio_files_by_emotion(args.input_file, args.input_audio_dir, args.target_output_dir)
    
    
    
    
    
    
