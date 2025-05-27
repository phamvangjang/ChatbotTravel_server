import speech_recognition as sr
from werkzeug.utils import secure_filename
import os
import tempfile

class SpeechService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
    
    def convert_speech_to_text(self, audio_file):
        """
        Convert speech from audio file to text
        Args:
            audio_file: FileStorage object containing the audio file
        Returns:
            str: Transcribed text or None if conversion fails
        """
        try:
            # Save the uploaded file temporarily
            filename = secure_filename(audio_file.filename)
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, filename)
            audio_file.save(temp_path)
            
            # Convert audio to text
            with sr.AudioFile(temp_path) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language='vi-VN')
            
            # Clean up temporary file
            os.remove(temp_path)
            
            return text
            
        except Exception as e:
            print(f"Error converting speech to text: {str(e)}")
            return None 