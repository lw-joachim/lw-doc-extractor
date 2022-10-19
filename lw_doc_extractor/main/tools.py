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

__author__ = 'Joachim Kestner <kestner@lightword.de>'

logger = logging.getLogger(__name__)

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
                               "is_cutscene" : n["type"].startswith("C-") }
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
    parser = argparse.ArgumentParser(description="Extract lines from compiler output"+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=ArgumentDefaultsHelpFormatter)
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
    parser = argparse.ArgumentParser(description="Generate audio files for "+"\n\nAuthor: {}\nVersion: {}".format(__author__,__version__), formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("input_file", help="The lines json file")
    parser.add_argument("--auth_file", required=True, help="The google server credentials file")
    parser.add_argument("ouput_directory", help="The output directory")
    
    k3logging.set_parser_log_arguments(parser)

    args = parser.parse_args()
    
    k3logging.eval_parser_log_arguments(args)
    
    with open(args.input_file) as fh:
        lineDictList = json.load(fh)
        
    generate_audio_files(lineDictList, args.ouput_directory, args.auth_file)
            
    logger.info(f"Final output written to {args.ouput_directory}")
    
