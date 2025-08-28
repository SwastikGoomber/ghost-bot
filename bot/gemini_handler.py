"""
Gemini API handler for chat, vision, and summary operations.
"""

import os
import base64
import json
import logging
from typing import Optional, Dict, List, Any, Tuple
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiHandler:
    """Handler for Gemini API interactions."""
    
    def __init__(self, api_key: str):
        """Initialize Gemini client."""
        self.client = genai.Client(api_key=api_key)
        self.function_declarations = self._setup_function_declarations()
    
    def _setup_function_declarations(self) -> List[types.FunctionDeclaration]:
        """Setup function declarations for Gemini native function calling."""
        return [
            types.FunctionDeclaration(
                name="cone_user",
                description="Apply a text transformation effect (cone) to a user's messages",
                parameters={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "The username or Discord ID to cone"
                        },
                        "effect": {
                            "type": "string",
                            "description": "The cone effect to apply",
                            "enum": ["uwu", "pirate", "shakespeare", "corporate", "caveman", 
                                   "valley", "baby", "yoda", "aussie", "scottish", "southern",
                                   "slayspeak", "brainrot", "scrum", "linkedin", "crisis",
                                   "canadian", "vsauce", "british", "oni", "dyslexia"]
                        },
                        "duration": {
                            "type": "string",
                            "description": "Duration like '5 minutes', '2 hours', or 'until they say sorry'"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Optional reason for coning"
                        }
                    },
                    "required": ["username", "effect", "duration"]
                }
            ),
            types.FunctionDeclaration(
                name="uncone_user",
                description="Remove text transformation effect (cone) from a user",
                parameters={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "The username or Discord ID to uncone"
                        }
                    },
                    "required": ["username"]
                }
            ),
            types.FunctionDeclaration(
                name="web_search",
                description="Search the web for current information",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        }
                    },
                    "required": ["query"]
                }
            )
        ]
    
    def get_chat_response(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: str,
        model: str = "gemini-2.5-flash-lite",
        enable_tools: bool = False,
        enable_web_search: bool = False
    ) -> Tuple[str, Optional[Dict]]:
        """
        Get chat response from Gemini.
        
        Returns:
            Tuple of (response_text, tool_call_dict or None)
        """
        try:
            # Convert messages to Gemini format
            contents = []
            
            # Add system prompt as first user message with context
            if system_prompt:
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"System context: {system_prompt}\n\nConversation:")]
                ))
            
            # Convert message history
            for msg in messages:
                role = "user" if msg.get("role") in ["user", "system"] else "model"
                text = msg.get("content", "")
                
                # Skip empty messages
                if not text:
                    continue
                    
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=text)]
                ))
            
            # Setup tools if enabled
            tools = []
            if enable_tools:
                tools.append(types.Tool(
                    function_declarations=self.function_declarations
                ))
            if enable_web_search:
                tools.append(types.Tool(googleSearch=types.GoogleSearch()))
            
            # Configure generation
            config = types.GenerateContentConfig(
                temperature=0.9,
                top_p=0.7,
                max_output_tokens=1000,
                tools=tools if tools else None
            )
            
            # Generate response
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            
            # Extract function calls if present
            tool_call = None
            try:
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                fc = part.function_call
                                if hasattr(fc, 'name') and fc.name:
                                    tool_call = {
                                        "tool": fc.name,
                                        "arguments": dict(fc.args) if hasattr(fc, 'args') and fc.args else {}
                                    }
                                    break
            except Exception as e:
                logger.error(f"Error parsing function calls: {e}")
                # Continue without function call
            
            # Get text response
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            return response_text, tool_call
            
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            raise
    
    def get_vision_response(
        self,
        messages: List[Dict[str, Any]],
        image_data: Optional[bytes] = None,
        system_prompt: str = "",
        model: str = "gemini-2.0-flash"
    ) -> str:
        """
        Get vision response from Gemini.
        
        Args:
            messages: Message history
            image_data: Raw image bytes
            system_prompt: System instructions
            model: Gemini model to use
            
        Returns:
            Response text
        """
        try:
            contents = []
            
            # Add system prompt
            if system_prompt:
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"System context: {system_prompt}\n")]
                ))
            
            # Process messages and find image
            for msg in messages:
                role = "user" if msg.get("role") in ["user", "system"] else "model"
                
                # Check for image in message
                if isinstance(msg.get("content"), list):
                    parts = []
                    for content_part in msg["content"]:
                        if content_part.get("type") == "text":
                            parts.append(types.Part.from_text(text=content_part["text"]))
                        elif content_part.get("type") == "image_url":
                            # Extract base64 image
                            url = content_part["image_url"]["url"]
                            if url.startswith("data:image"):
                                base64_data = url.split(",")[1]
                                image_bytes = base64.b64decode(base64_data)
                                parts.append(types.Part.from_bytes(
                                    mime_type="image/jpeg",
                                    data=image_bytes
                                ))
                    
                    if parts:
                        contents.append(types.Content(role=role, parts=parts))
                else:
                    # Regular text message
                    text = msg.get("content", "")
                    if text:
                        contents.append(types.Content(
                            role=role,
                            parts=[types.Part.from_text(text=text)]
                        ))
            
            # Add standalone image if provided
            if image_data:
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_bytes(
                        mime_type="image/jpeg",
                        data=image_data
                    )]
                ))
            
            # Configure generation
            config = types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.8,
                max_output_tokens=500
            )
            
            # Generate response
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            
            # Get text response with proper error handling
            response_text = ""
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text += part.text
            
            if response_text:
                return response_text
            else:
                # Use existing error responses for user-facing errors
                import random
                from config import ERROR_RESPONSES
                return random.choice(ERROR_RESPONSES)
            
        except Exception as e:
            logger.error(f"Gemini vision error: {e}")
            raise
    
    def get_summary_response(
        self,
        text: str,
        model: str = "gemini-2.5-flash-lite"
    ) -> str:
        """
        Get summary from Gemini.
        
        Args:
            text: Text to summarize
            model: Gemini model to use
            
        Returns:
            Summary text
        """
        try:
            prompt = f"""Summarize this conversation concisely, focusing on key points and any relationship developments:

{text}

Provide a brief summary (2-3 sentences max):"""

            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)]
                )
            ]
            
            config = types.GenerateContentConfig(
                temperature=0.3,
                top_p=0.9,
                max_output_tokens=200
            )
            
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            
            return response.text if hasattr(response, 'text') else str(response)
            
        except Exception as e:
            logger.error(f"Gemini summary error: {e}")
            raise
