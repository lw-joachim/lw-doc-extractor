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

def _clear_files(dirPath):
    for filename in os.listdir(dirPath):
        file_path = os.path.join(dirPath, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)

def get_all_lines(compOutDict):
    retLines = []
    errCnt = 0
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
                    if k == "stage_directions":
                        continue
                    elif k == "text":
                        if v == None:
                            logger.info(f"Line does not contain any spoken text. Ignoring. ID {intrDict['external_id']}")
                            break
                    elif v == None:
                        logger.error(f"A line has a null value for {k} which is not allowed. Line id: {diaLineDict['id']}, parent node id: {diaLineDict['parent_node_id']}")
                        errCnt += 1
                else:
                    retLines.append(diaLineDict)
    if errCnt > 0:
        raise RuntimeError(f"Encountered errors on {errCnt} lines")
    return retLines

def extract_dialog_lines():
    parser = argparse.ArgumentParser(description="Extract lines from compiler output."+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("input_file", help="The compiler output json file")
    parser.add_argument("output_file", help="The output json file")
    k3logging.set_parser_log_arguments(parser)

    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
    with open(args.input_file) as fh:
        compOutDict = json.load(fh)
        
    with open(args.output_file, "w") as fh:
        lineDicts = get_all_lines(compOutDict)
        json.dump(lineDicts, fh, indent=2)
        logger.info(f"Writing lines to {args.output_file}")
    logger.info(f"Final output written to {args.output_file}")
    
def generate_audio_recording_files(compilerOutput, outputDir):
    
    nodeIdToTypeMap = get_node_to_types(compilerOutput)
    nodeIdToDescrMap = get_node_to_description(compilerOutput)
    lineDictList = get_all_lines(compilerOutput)
    
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


def generate_audio_files(lineDictList, outputDirectory, authFile):
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
    numLines = len(lineDictList)
    logger.info(f"Generating audio files for {numLines} audio lines")
    for i, lineDict in enumerate(lineDictList):
        if i % 20 == 0 and i != 0:
            logger.info(f"Generated {i} audio files out of {numLines}")
        outfile = os.path.join(outputDirectory, lineDict["id"]+".mp3")
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
        

def generate_audio_files_cli():
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
    
    generate_audio_files(lineDictList, args.ouput_directory, args.auth_file)
    
    logger.info(f"Final output written to {args.ouput_directory}")
    
def update_story_chapter(scriptInputFile, projectDirectory, googleAuthFile, articyConfigPath, dryRun, workingDir):
    
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
    genAudioDir    = os.path.join(audioDir, "GeneratedAudio")
    recAudioDir    = os.path.join(audioDir, "RecordedVoicelines")
    
    _mkdir_ignore_exists(genFilesDir)
    _mkdir_ignore_exists(scriptDir)
    _mkdir_ignore_exists(audioScriptDir)
    _mkdir_ignore_exists(genAudioDir)
    _mkdir_ignore_exists(recAudioDir)
    
    _clear_files(genFilesDir)
    _clear_files(scriptDir)
    _clear_files(audioScriptDir)
    _clear_files(genAudioDir)
    
    shutil.copy(tmpCompOutFile, os.path.join(genFilesDir, "compiler_output.json"))
    
    shutil.copy(scriptInputFile, os.path.join(scriptDir, f"{chapterId}.docx"))
    shutil.copy(tmpRawOutFile, os.path.join(scriptDir, f"{chapterId}_raw.txt"))
    
    targetProject = articyConfig["test_project"] if dryRun else articyConfig["project"]
    
    authFile = os.path.join(tmpDir, "authfile")
    
    with open(authFile, "w") as fh:
        fh.write("{}\n{}".format(articyConfig["user"], articyConfig["password"]))
    
    cli.run_populator(tmpCompOutFile, targetProject, "One", "-v", articyConfig["iron_python"], articyConfig["server_host"], articyConfig["server_port"], authFile, articyConfig["articy_api_lib"])

    generate_audio_recording_files(compOutDict, audioScriptDir)

    if not dryRun:
        generate_audio_files(get_all_lines(compOutDict), genAudioDir, googleAuthFile)
        
    logger.info("Update story chapter process complete")
    
def update_story_chapter_cli():
    parser = argparse.ArgumentParser(description="Update story chapter in project. "+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("input_file", help="The input document file")
    parser.add_argument("project_directory", help="The directory of the project")
    parser.add_argument("--gauth", required=True, help="The google server json credentials file. Required.")
    parser.add_argument("--articy-config", required=True, help="Json file containing the the articy configuration. Parameter is required. Required keys are:\ntest_project, project: the test and production articy projects\nuser, password: the articy username and pass\nserver_host, server_port: articy server host and port\niron_python: iron python exe path\narticy_api_lib: path to the articy api")
    parser.add_argument("--dry-run", action="store_true", help="If flag is set project directory will not be changed and import will happen into a test directory and test articy project")
    parser.add_argument("--dry-run-dir", help="A directory that can be specified that will be used instead of a temporary directory for debugging. Only can be used in combination with dry-run")
    
    k3logging.set_parser_log_arguments(parser)

    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
    
    if args.dry_run and args.dry_run_dir:
        tmpDir = args.dry_run_dir
    else:
        tmpDirHandle = tempfile.TemporaryDirectory()
        tmpDir = tmpDirHandle.name
    
    update_story_chapter(args.input_file, args.project_directory, args.gauth, args.articy_config, args.dry_run, tmpDir)
    
def sort_audio_files_by_emotion_cli():
    parser = argparse.ArgumentParser(description="Sort audio files by emotion. "+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("input_file", help="The compiler output json file")
    parser.add_argument("input_audio_dir", help="The input directory with all audio files")
    parser.add_argument("target_output_dir", help="The output directory into which the sorted files will be placed")
    
    k3logging.set_parser_log_arguments(parser)

    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
    
    with open(args.input_file) as fh:
        compOutDict = json.load(fh)
    
    
    emotionToFileMap = {}
    
    lineDicts = get_all_lines(compOutDict)
    
    for lineDict in lineDicts:
        if "emotion" in lineDict["line_attributes"]:
            emotionVal = lineDict["line_attributes"]["emotion"]
            if emotionVal not in emotionToFileMap:
                emotionToFileMap[emotionVal] = []
            
            emotionToFileMap[emotionVal].append(lineDict["id"])
        else:
            if "default" not in emotionToFileMap:
                emotionToFileMap["default"] = []
            emotionToFileMap["default"].append(lineDict["id"])
            
    logger.info(f"Found the following emotions: {emotionToFileMap.keys()}")
            
    for em in sorted(emotionToFileMap.keys()):
        emTarDir = os.path.join(args.target_output_dir, em)
        
        os.mkdir(emTarDir)
        
        for lineId in emotionToFileMap[em]:
            
            fileNm = f"{lineId}.mp3"
            srcFilePath = os.path.join(args.input_audio_dir, fileNm)
            
            if not os.path.isfile(srcFilePath):
                raise RuntimeError(f"Missing audio file {srcFilePath}")
            
            tarFilePath = os.path.join(emTarDir, fileNm)
            shutil.copy(srcFilePath, tarFilePath)
            logger.debug(f"Copied {srcFilePath} to {tarFilePath}")
            
        logger.info(f"Copied {len(emotionToFileMap[em])} audio files for emotion {em}")
        
    logger.info("Completed grouping audio files by emotion")
    
    
    
    
