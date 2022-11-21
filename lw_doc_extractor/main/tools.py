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
import errno
import json
from argparse import RawDescriptionHelpFormatter, ArgumentDefaultsHelpFormatter
import random
import time
import collections
import csv

__author__ = 'Joachim Kestner <kestner@lightword.de>'

logger = logging.getLogger(__name__)

def get_node_to_types(compOutDict):
    #"is_cutscene" : n["type"].startswith("C-")
    return {n["id"] : n["type"]  for n in compOutDict["nodes"]}
    
def get_node_to_description(compOutDict):
    #"is_cutscene" : n["type"].startswith("C-")
    return {n["id"] : n["description"]  for n in compOutDict["nodes"]}

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
                               "stage_directions" : intrDict["parameters"]["stage_directions"]}
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
        
    with open(args.output_file) as fh:
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
            targetPath = os.path.join(outputDir, f"{sp}_lines_for_recoreding.txt")
            targetComplPath = os.path.join(outputDir, f"{sp}_lines_for_recoreding_with_others.txt")
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
        
    # for sp in characterToDialogToLines:
    #     ct = 0
    #     targetPath = os.path.join(outputDir, f"{sp}_lines_for_recoreding.txt")
    #     with open(targetPath, "w", encoding="utf-8") as fh:
    #         for ch in characterToDialogToLines[sp]:
    #             titleStr = nodeIdToTypeMap[ch] + " "+ ch
    #             fh.write("\n\n"+ titleStr + "\n" + "="*len(titleStr) +"\n")
    #             if nodeIdToDescrMap[ch]:
    #                 fh.write(nodeIdToDescrMap[ch] + "\n" + "-"*len(titleStr) +"\n")
    #             for lineD in characterToDialogToLines[sp][ch]:
    #                 fh.write("\n")
    #                 if lineD["stage_directions"]:
    #                     fh.write("(" + lineD["stage_directions"] + ")\n")
    #                 fh.write(lineD["text"] + "\n")
    #                 ct += 1
    #                 linesForMasterCsv.append(lineD)
    #
    #     logger.info(f"Written {ct} lines for speaker {sp} to {targetPath}")
    #
    # with open(os.path.join(outputDir, 'audio_line_referece.csv'), 'w', newline='') as csvfile:
    #     fieldnames = ['speaker', 'parent_node_id', "text", "id"]
    #     writer = csv.DictWriter(csvfile, fieldnames=fieldnames, dialect='excel',  extrasaction='ignore')
    #     writer.writeheader()
    #
    #     for line in linesForMasterCsv:
    #         writer.writerow(line)
            
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
            speed = random.uniform(0.93, 1.04)
            pitch = random.uniform(-10.0, 5.0)
            mappedSpeakerToVoiceMap[lineDict["speaker"]] = voice, speed, pitch
        
        speechGenClient.synthesize_speech(lineDict["text"], outfile, voice, speed, pitch)
        time.sleep(0.05)
        
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
    
