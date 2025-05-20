import os
import whisper
from typing import Optional
import tempfile

class SpeechService:
    def __init__(self):
        # Load Whisper model
        self.model = whisper.load_model("base")
        
    def convert_speech_to_text(self, audio_file) -> Optional[str]:
        """Convert speech to text using OpenAI Whisper"""
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                audio_file.save(temp_file.name)
                
                # Transcribe audio
                result = self.model.transcribe(temp_file.name)
                
                # Clean up temporary file
                os.unlink(temp_file.name)
                
                return result["text"]
                
        except Exception as e:
            print(f"Error converting speech to text: {e}")
            return None

# Initialize speech service
speech_service = SpeechService() 