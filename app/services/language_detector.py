import logging
from typing import Dict, Optional
import openai
import re
import json
import os
from datetime import datetime

# Configure logging
def setup_logger():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Create a logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    # Create handlers
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler
    log_file = f'logs/language_detector_{datetime.now().strftime("%Y%m%d")}.log'
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatters and add it to handlers
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)
    
    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Initialize logger
logger = setup_logger()

class LanguageDetector:
    SUPPORTED_LANGUAGES = {
        'vi': 'Vietnamese',
        'zh-CN': 'Chinese (Simplified)',
        'ko': 'Korean',
        'en': 'English',
        'ja': 'Japanese'
    }
    
    # Common words and patterns for each language
    LANGUAGE_PATTERNS = {
        'vi': [
            r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]',
            r'\b(tôi|bạn|của|và|là|có|không|được|cho|với|này|đó|đây|kia|nào|sao|bao|giờ|đâu|ai|gì|nhiều|ít|lớn|nhỏ|cao|thấp|dài|ngắn|rộng|hẹp|đẹp|xấu|tốt|kém|hay|dở|đúng|sai)\b'
        ],
        'zh-CN': [
            r'[\u4e00-\u9fff]',
            r'\b(我|你|他|她|它|们|的|是|在|有|和|这|那|什么|为什么|怎么|多少|谁|哪里|什么时候|好|坏|大|小|高|低|长|短|宽|窄|美|丑|对|错)\b'
        ],
        'ko': [
            r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f\ua960-\ua97f\ud7b0-\ud7ff]',
            r'\b(나|너|그|그녀|그것|들|의|이다|있다|없다|이|그|무엇|왜|어떻게|얼마나|누구|어디|언제|좋은|나쁜|큰|작은|높은|낮은|긴|짧은|넓은|좁은|아름다운|추한|맞는|틀린)\b'
        ],
        'ja': [
            r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]',
            r'\b(私|あなた|彼|彼女|それ|たち|の|です|ある|ない|これ|それ|何|なぜ|どう|いくつ|誰|どこ|いつ|良い|悪い|大きい|小さい|高い|低い|長い|短い|広い|狭い|美しい|醜い|正しい|間違った)\b'
        ],
        'en': [
            r'\b(I|you|he|she|it|they|the|is|are|was|were|have|has|had|and|or|but|this|that|what|why|how|many|who|where|when|good|bad|big|small|high|low|long|short|wide|narrow|beautiful|ugly|right|wrong)\b'
        ]
    }
    
    def __init__(self):
        self.openai = openai
        
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the input text using both pattern matching and OpenAI.
        Returns the detected language code.
        """
        try:
            if not text or not isinstance(text, str):
                logger.warning("Empty or invalid input text, defaulting to English")
                return 'en'
                
            logger.info(f"Detecting language for input text: {text[:100]}...")
            
            # First try pattern matching
            pattern_detection = self._detect_by_patterns(text)
            if pattern_detection:
                logger.info(f"Language detected by patterns: {self.SUPPORTED_LANGUAGES[pattern_detection]}")
                print("pattern_detection: " + pattern_detection)
                return pattern_detection
            
            # If pattern matching fails, use OpenAI
            logger.info("Pattern matching failed, using OpenAI for detection...")
            
            prompt = f"""Analyze the following text and determine its language. 
            Respond with ONLY ONE of these language codes: vi (Vietnamese), zh-CN (Chinese Simplified), ko (Korean), en (English), or ja (Japanese).
            If the language is not one of these, respond with 'en'.
            
            Text: {text}
            
            Language code:"""
            
            try:
                response = self.openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a language detection expert. Respond with ONLY the language code."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=10
                )
                
                if not response or not hasattr(response, 'choices') or not response.choices:
                    logger.error("Empty response from OpenAI")
                    return 'en'
                    
                detected_lang = response.choices[0].message.content.strip().lower()
                logger.info(f"Raw OpenAI response: {detected_lang}")
                
                # Normalize Chinese language code
                if detected_lang.startswith('zh'):
                    detected_lang = 'zh-CN'
                
                # Validate the detected language
                if detected_lang in self.SUPPORTED_LANGUAGES:
                    logger.info(f"OpenAI detected language: {self.SUPPORTED_LANGUAGES[detected_lang]}")
                    return detected_lang
                else:
                    logger.warning(f"Unsupported language detected: {detected_lang}, defaulting to English")
                    return 'en'
                    
            except Exception as openai_error:
                logger.error(f"OpenAI API error: {str(openai_error)}")
                return 'en'
                
        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            return 'en'
            
    def _detect_by_patterns(self, text: str) -> Optional[str]:
        """Detect language using pattern matching"""
        try:
            # Count matches for each language
            scores = {}
            for lang, patterns in self.LANGUAGE_PATTERNS.items():
                score = 0
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    score += len(matches)
                scores[lang] = score
                logger.debug(f"Pattern matching score for {lang}: {score}")
            
            # Get the language with the highest score
            if scores:
                max_score = max(scores.values())
                if max_score > 0:
                    detected_lang = max(scores.items(), key=lambda x: x[1])[0]
                    logger.info(f"Pattern matching scores: {json.dumps(scores, indent=2)}")
                    return detected_lang
            
            logger.info("No language patterns matched")
            return None
            
        except Exception as e:
            logger.error(f"Error in pattern matching: {str(e)}")
            return None
            
    def get_language_name(self, lang_code: str) -> str:
        """Get the full name of a language from its code"""
        return self.SUPPORTED_LANGUAGES.get(lang_code, 'English')
        
    def is_supported_language(self, lang_code: str) -> bool:
        """Check if a language code is supported"""
        return lang_code in self.SUPPORTED_LANGUAGES 