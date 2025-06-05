import openai
import os
import json
import logging
from datetime import datetime, time
from typing import Optional, Dict

# Initialize logger
logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')
        logger.info("OpenAI service initialized")
    
    def generate_response(self, message):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are a travel assistant specializing in Vietnamese destinations. 
                    When providing travel recommendations, structure your response in a way that includes:
                    1. A detailed text response
                    2. An itinerary object with the following structure:
                    {
                        "destination": "city name",
                        "total_days": number of days,
                        "estimated_cost": estimated cost in VND,
                        "locations": [list of location names],
                        "activities": [
                            {
                                "day": day number,
                                "title": activity title,
                                "description": activity description,
                                "location": location name,
                                "full_address": full address of the location,
                                "start_time": "HH:MM",
                                "end_time": "HH:MM"
                            }
                        ]
                    }
                    Make sure to include specific locations that can be mapped.
                    Format the itinerary as a JSON object after the text response."""},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse response and extract itinerary if present
            response_text = response.choices[0].message.content
            logger.info("Received response from OpenAI")
            itinerary = self._extract_itinerary(response_text)
            
            return {
                'text': response_text,
                'itinerary': itinerary
            }
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                'text': f"I apologize, but I encountered an error: {str(e)}",
                'itinerary': None
            }
    
    def _extract_itinerary(self, text):
        try:
            # Try to find JSON object in the text
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = text[json_start:json_end]
                try:
                    itinerary_data = json.loads(json_str)
                    return itinerary_data
                except json.JSONDecodeError:
                    print("Failed to parse JSON from response")
            
            # Fallback to text parsing if JSON extraction fails
            locations = []
            activities = []
            current_day = None
            current_activity = None
            
            # Split text into lines for processing
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Check for day markers
                if "Ngày" in line or "Day" in line:
                    if current_activity:
                        activities.append(current_activity)
                    current_day = int(line.split()[1].replace(':', ''))
                    current_activity = None
                    continue
                
                # Check for location mentions
                if ":" in line and not line.startswith("Ngày") and not line.startswith("Day"):
                    location = line.split(':')[0].strip()
                    if location and location not in locations:
                        locations.append(location)
                    
                    # Create activity entry
                    if current_activity:
                        activities.append(current_activity)
                    
                    current_activity = {
                        'day': current_day,
                        'title': location,
                        'description': line.split(':')[1].strip() if ':' in line else line,
                        'location': location,
                        'start_time': "09:00",  # Default start time
                        'end_time': "17:00"     # Default end time
                    }
            
            # Add the last activity if exists
            if current_activity:
                activities.append(current_activity)
            
            # Create itinerary structure
            if locations:
                return {
                    'destination': 'Ho Chi Minh City',
                    'total_days': max([act['day'] for act in activities]) if activities else 1,
                    'estimated_cost': 5000000,  # Default cost in VND
                    'locations': locations,
                    'activities': activities
                }
            
            return None
            
        except Exception as e:
            print(f"Error extracting itinerary: {str(e)}")
            return None 