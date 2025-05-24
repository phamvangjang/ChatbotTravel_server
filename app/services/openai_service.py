import os
import openai
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        logger.info("Initializing OpenAI service...")
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.error("OPENAI_API_KEY environment variable is not set")
            raise ValueError("OPENAI_API_KEY environment variable is not set")
            
        openai.api_key = self.api_key
        logger.info("OpenAI service initialized successfully")
        
    def analyze_travel_query(self, query: str, travel_data: Dict) -> Dict:
        """Analyze travel query and generate recommendations"""
        try:
            logger.info(f"Analyzing travel query: {query}")
            
            # Prepare context from travel data
            context = self._prepare_context(travel_data)
            logger.debug(f"Prepared context length: {len(context)}")
            
            # Construct prompt
            prompt = f"""Based on the following travel information about Ho Chi Minh City, please create a personalized travel itinerary.

Travel Information:
{context}

User Query: {query}

Please provide a detailed response in the following JSON format:
{{
    "itinerary": [
        {{
            "day": 1,
            "activities": [
                {{
                    "time": "HH:MM",
                    "name": "Activity name",
                    "description": "Detailed description",
                    "location": {{
                        "name": "Location name",
                        "address": "Full address"
                    }},
                    "estimated_cost": "Cost in VND"
                }}
            ]
        }}
    ],
    "tips": [
        "Tip 1",
        "Tip 2"
    ],
    "transportation": "Transportation advice",
    "total_cost": "Total estimated cost in VND"
}}

IMPORTANT: Your response must be a valid JSON object. Do not include any text before or after the JSON object.
Ensure the itinerary is realistic, considering:
1. Opening hours of attractions
2. Travel time between locations
3. Local customs and culture
4. Weather conditions
5. Budget constraints
"""
            
            logger.debug("Sending request to OpenAI API...")
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful travel assistant specializing in Ho Chi Minh City tourism. You must respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Extract and parse response
            content = response.choices[0].message.content.strip()
            logger.debug(f"Received response from OpenAI: {content[:200]}...")
            
            try:
                # Clean the response to ensure it's valid JSON
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                result = json.loads(content)
                logger.info("Successfully parsed OpenAI response")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response as JSON: {str(e)}")
                logger.error(f"Raw response: {content}")
                # Return a basic error response
                return {
                    'error': 'Failed to parse response from AI',
                    'itinerary': [],
                    'tips': ['Please try again with a different query'],
                    'transportation': 'Unable to provide transportation advice',
                    'total_cost': 'N/A'
                }
                
        except Exception as e:
            logger.error(f"Error in analyze_travel_query: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'itinerary': [],
                'tips': ['An error occurred while processing your request'],
                'transportation': 'Unable to provide transportation advice',
                'total_cost': 'N/A'
            }
            
    def translate_text(self, text: str, target_lang: str) -> str:
        """Translate text to target language"""
        try:
            logger.info(f"Translating text to {target_lang}")
            logger.debug(f"Text to translate: {text[:100]}...")
            
            prompt = f"""Translate the following text to {target_lang}. Maintain the original meaning and tone:

{text}

Translation:"""
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are a professional translator specializing in {target_lang}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            translation = response.choices[0].message.content.strip()
            logger.info("Translation completed successfully")
            return translation
            
        except Exception as e:
            logger.error(f"Error in translate_text: {str(e)}", exc_info=True)
            return text
            
    def _prepare_context(self, travel_data: Dict) -> str:
        """Prepare context string from travel data"""
        try:
            logger.debug("Preparing context from travel data")
            context_parts = []
            
            # Add attractions
            if 'attractions' in travel_data:
                context_parts.append("Attractions:")
                for attraction in travel_data['attractions']:
                    context_parts.append(f"- {attraction['name']}: {attraction['description']}")
                    
            # Add cuisine
            if 'cuisine' in travel_data:
                context_parts.append("\nLocal Cuisine:")
                for dish in travel_data['cuisine']:
                    context_parts.append(f"- {dish['name']}: {dish['description']}")
                    
            # Add transportation
            if 'transportation' in travel_data:
                context_parts.append("\nTransportation:")
                context_parts.append(travel_data['transportation'])
                
            # Add accommodation
            if 'accommodation' in travel_data:
                context_parts.append("\nAccommodation:")
                for option in travel_data['accommodation']:
                    context_parts.append(f"- {option['type']}: {option['description']}")
                    
            # Add weather
            if 'weather' in travel_data:
                context_parts.append("\nWeather:")
                context_parts.append(travel_data['weather'])
                
            # Add tips
            if 'tips' in travel_data:
                context_parts.append("\nTravel Tips:")
                for tip in travel_data['tips']:
                    context_parts.append(f"- {tip}")
                    
            context = "\n".join(context_parts)
            logger.debug(f"Context prepared successfully, length: {len(context)}")
            return context
            
        except Exception as e:
            logger.error(f"Error preparing context: {str(e)}", exc_info=True)
            return ""

# Initialize OpenAI service
try:
    logger.info("Creating OpenAI service instance...")
    openai_service = OpenAIService()
    logger.info("OpenAI service instance created successfully")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI service: {str(e)}", exc_info=True)
    openai_service = None 