import sys, os, logging
from google.cloud import texttospeech

def set_google_application_credentials_global(filePath):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(filePath)
    
logger = logging.getLogger(__name__)

voice_dict = {"en-AU-Wavenet-C": "FEMALE",
              "en-AU-Wavenet-B" : "MALE",
             "en-AU-Wavenet-D": "MALE",
             "en-AU-Neural2-A": "FEMALE",
             "en-AU-Neural2-C": "FEMALE",
             "en-AU-Neural2-D": "MALE",
             "en-IN-Wavenet-C": "MALE",
             "en-GB-Wavenet-B": "MALE",
             "en-GB-Wavenet-D": "MALE",
             "en-GB-Neural2-A": "FEMALE",
             "en-GB-Neural2-B": "MALE",
             "en-GB-Neural2-C": "FEMALE",
             "en-GB-Neural2-D": "MALE",
             "en-US-Neural2-A": "MALE",
             "en-US-Neural2-F": "FEMALE"
             }

class GTextToSpeechClient:
    
    def __init__(self, credentialsFilePath):
        set_google_application_credentials_global(credentialsFilePath)
        self.client = texttospeech.TextToSpeechClient()
        

    def synthesize_speech(self, text, outfile, voice, speed=1.0, pitch=0.0):
        """Synthesizes speech from the input string of text."""
        
        gender = voice_dict[voice]
    
        input_text = texttospeech.SynthesisInput(text=text)
    
        # Note: the voice can also be specified by name.
        # Names of voices can be retrieved with client.list_voices().
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice[:5], #"en-GB",
            name=voice,
            ssml_gender=texttospeech.SsmlVoiceGender.MALE if gender == "MALE" else texttospeech.SsmlVoiceGender.FEMALE
        )
    
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=speed, #1.0,
            pitch=pitch# 0.0, #  range [-20.0, 20.0]
        )
    
        response = self.client.synthesize_speech(
            request={"input": input_text, "voice": voice, "audio_config": audio_config}
        )
        
        # The response's audio_content is binary.
        with open(outfile, "wb") as out:
            out.write(response.audio_content)
        logger.debug(f'Created audio output file {outfile}')