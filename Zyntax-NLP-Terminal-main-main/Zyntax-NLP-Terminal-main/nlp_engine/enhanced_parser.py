"""
File: enhanced_parser.py
Description: An improved version of the parser with context awareness, 
             better entity extraction, and learning capabilities.
"""

import spacy
import json
import os
from pathlib import Path
from rapidfuzz import process, fuzz
from spacy.tokens import Doc
from spacy.matcher import PhraseMatcher, Matcher
from typing import Dict, List, Tuple, Optional, Any

class CommandHistory:
    """Tracks command history and provides context for future commands"""
    
    def __init__(self, history_size=10):
        self.commands = []
        self.history_size = history_size
        self.last_entities = {}  # Store entities from previous commands
    
    def add_command(self, command_dict: Dict[str, Any]) -> None:
        """Add a command to history and update context"""
        self.commands.append(command_dict)
        
        # Update last entities for reference resolution
        if 'entities' in command_dict:
            for entity_type, values in command_dict['entities'].items():
                if values:  # Only update if there are values
                    self.last_entities[entity_type] = values
        
        # Trim history if necessary
        if len(self.commands) > self.history_size:
            self.commands.pop(0)
    
    def get_last_command(self) -> Optional[Dict[str, Any]]:
        """Return the most recent command"""
        if self.commands:
            return self.commands[-1]
        return None
    
    def get_entity_context(self) -> Dict[str, List[str]]:
        """Return context of previously mentioned entities"""
        return self.last_entities


class EnhancedParser:
    """
    Enhanced parser with context awareness, improved entity extraction,
    and learning capabilities.
    """
    
    def __init__(self, user_config_path: str = None):
        # Load spaCy model
        self.nlp = spacy.load("en_core_web_sm")
        
        # Command history for context
        self.history = CommandHistory()
        
        # Default command mappings
        self.base_action_keywords = {
            # File/Directory Listing & Navigation
            "list files": "list_files", 
            "show files": "list_files", 
            "ls": "list_files",
            "show current directory": "show_path",
            "pwd": "show_path",
            "change directory": "change_directory", 
            "cd": "change_directory",
            
            # Many more commands would be defined here...
        }
        
        # Load user customizations if available
        self.user_action_keywords = {}
        if user_config_path:
            self._load_user_mappings(user_config_path)
        
        # Combined mappings (user overrides base)
        self.action_keywords = {**self.base_action_keywords, **self.user_action_keywords}
        
        # Initialize matchers
        self._setup_matchers()
        
        # Configuration
        self.fuzzy_match_threshold_execute = 90
        self.fuzzy_match_threshold_suggest = 65
        
        # Command learning storage
        self.learning_data_path = Path.home() / ".zyntax" / "learning_data.json"
        self.learning_data = self._load_learning_data()
    
    def _load_user_mappings(self, config_path: str) -> None:
        """Load user-defined command mappings"""
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                if 'command_mappings' in user_config:
                    self.user_action_keywords = user_config['command_mappings']
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load user config: {e}")
    
    def _load_learning_data(self) -> Dict:
        """Load learning data from disk"""
        try:
            if self.learning_data_path.exists():
                with open(self.learning_data_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load learning data: {e}")
        
        # Return empty structure if loading fails
        return {
            "successful_parses": {},
            "misinterpreted_commands": [],
            "user_corrections": {},
            "command_frequencies": {}
        }
    
    def _save_learning_data(self) -> None:
        """Save learning data to disk"""
        try:
            # Ensure directory exists
            self.learning_data_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.learning_data_path, 'w') as f:
                json.dump(self.learning_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save learning data: {e}")
    
    def _setup_matchers(self) -> None:
        """Set up spaCy matchers for specialized entity recognition"""
        # Phrase matcher for exact command matches
        self.command_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        for phrase in self.action_keywords.keys():
            if " " in phrase:  # Only add multi-word phrases
                self.command_matcher.add(phrase, [self.nlp(phrase)])
        
        # Pattern matcher for file paths and other specialized entities
        self.entity_matcher = Matcher(self.nlp.vocab)
        
        # File path patterns (very simplified example)
        file_path_pattern = [
            {"TEXT": {"REGEX": r"[\/\w\.\-]+"}, "OP": "+"}
        ]
        self.entity_matcher.add("FILE_PATH", [file_path_pattern])
        
        # Add more specialized patterns as needed
    
    def _extract_specialized_entities(self, doc: Doc) -> Dict[str, List[str]]:
        """Extract specialized entities like file paths using custom patterns"""
        entities = {"file_paths": [], "git_branches": [], "options": []}
        
        # Use the entity matcher
        matches = self.entity_matcher(doc)
        for match_id, start, end in matches:
            match_text = doc[start:end].text
            rule_id = self.nlp.vocab.strings[match_id]
            
            if rule_id == "FILE_PATH":
                entities["file_paths"].append(match_text)
        
        # Extract options (flags like -m, --verbose)
        for token in doc:
            if token.text.startswith("-"):
                entities["options"].append(token.text)
        
        return entities
    
    def _extract_arguments(self, doc: Doc, action_id: str, context: Dict) -> Dict:
        """
        Extract and validate arguments for a specific action,
        considering context from previous commands
        """
        # This would be a much more sophisticated version of your existing
        # extract_relevant_entities function
        
        # First get basic entities
        basic_entities = self._extract_basic_entities(doc)
        
        # Then get specialized entities
        specialized_entities = self._extract_specialized_entities(doc)
        
        # Combine all entities
        all_entities = {**basic_entities, **specialized_entities}
        
        # Resolve references like "that file" using context
        resolved_entities = self._resolve_references(doc, all_entities, context)
        
        # Format arguments appropriately for the specific action
        formatted_args = self._format_args_for_action(action_id, resolved_entities)
        
        return {
            "raw_entities": all_entities,
            "resolved_entities": resolved_entities,
            "formatted_args": formatted_args
        }
    
    def _extract_basic_entities(self, doc: Doc) -> Dict[str, List[str]]:
        """Extract basic entities using spaCy's built-in capabilities"""
        entities = {"nouns": [], "proper_nouns": []}
        
        for token in doc:
            if token.pos_ == "NOUN" and not token.is_stop:
                entities["nouns"].append(token.text)
            elif token.pos_ == "PROPN":
                entities["proper_nouns"].append(token.text)
        
        return entities
    
    def _resolve_references(self, doc: Doc, entities: Dict, context: Dict) -> Dict:
        """Resolve references like 'that file' using context"""
        resolved = entities.copy()
        
        # Check for reference indicators
        has_reference = any(token.text.lower() in ["that", "this", "it", "those"] for token in doc)
        
        if has_reference and context:
            # Simple example: if user mentions "that file" and we have files in context
            for token in doc:
                if token.lower_ in ["that", "this"] and token.i + 1 < len(doc):
                    next_token = doc[token.i + 1]
                    if next_token.lower_ in ["file", "directory", "folder"]:
                        entity_type = "file_paths" if next_token.lower_ == "file" else "directory_paths"
                        if entity_type in context and context[entity_type]:
                            # Add the previously mentioned entity to our resolved entities
                            if entity_type not in resolved:
                                resolved[entity_type] = []
                            resolved[entity_type].append(context[entity_type][0])
        
        return resolved
    
    def _format_args_for_action(self, action_id: str, entities: Dict) -> List[str]:
        """Format extracted entities into appropriate arguments for the action"""
        args = []
        
        # Different actions need different arguments
        if action_id in ["change_directory", "make_directory", "delete_directory"]:
            # Prioritize directory paths, fall back to file paths
            if "directory_paths" in entities and entities["directory_paths"]:
                args.append(entities["directory_paths"][0])
            elif "file_paths" in entities and entities["file_paths"]:
                args.append(entities["file_paths"][0])
        
        elif action_id in ["create_file", "delete_file", "display_file"]:
            if "file_paths" in entities and entities["file_paths"]:
                args.append(entities["file_paths"][0])
        
        elif action_id in ["move_rename", "copy_file"]:
            # These need both source and destination
            if "file_paths" in entities and len(entities["file_paths"]) >= 2:
                args.extend(entities["file_paths"][:2])
        
        # Add any option flags
        if "options" in entities:
            args.extend(entities["options"])
        
        return args
    
    def parse_input(self, text: str) -> Dict:
        """
        Parse natural language input into a structured command.
        Uses context from previous commands and learns from user feedback.
        """
        if not text.strip():
            return None
        
        # Process the text with spaCy
        doc = self.nlp(text)
        
        # Get context from command history
        context = self.history.get_entity_context()
        
        # 1. Intent Recognition using multiple strategies
        
        # First try exact matches using the phrase matcher
        command_matches = self.command_matcher(doc)
        exact_match = None
        if command_matches:
            match_id, start, end = command_matches[0]
            matched_phrase = doc[start:end].text.lower()
            exact_match = self.action_keywords.get(matched_phrase)
        
        # If no exact match, try fuzzy matching
        if not exact_match:
            match_result = process.extractOne(
                text.lower(),
                self.action_keywords.keys(),
                scorer=fuzz.WRatio,
                score_cutoff=self.fuzzy_match_threshold_suggest
            )
            
            action_id = None
            suggestion_action_id = None
            suggestion_phrase = None
            
            if match_result:
                matched_phrase, score, _ = match_result
                if score >= self.fuzzy_match_threshold_execute:
                    action_id = self.action_keywords[matched_phrase]
                elif score >= self.fuzzy_match_threshold_suggest:
                    suggestion_action_id = self.action_keywords[matched_phrase]
                    suggestion_phrase = matched_phrase
        else:
            action_id = exact_match
            
        # Apply learning: Check if similar inputs have been corrected before
        learned_action = self._check_learning_data(text)
        if learned_action:
            action_id = learned_action
        
        # If no action is identified or suggested, treat as unrecognized
        if not action_id and not suggestion_action_id:
            return {'action': 'unrecognized'}
        
        # If only a suggestion was found, return suggestion structure
        if not action_id and suggestion_action_id:
            return {
                'action': 'suggest', 
                'suggestion_action_id': suggestion_action_id, 
                'suggestion_phrase': suggestion_phrase
            }
        
        # 2. Extract entities and arguments
        entity_data = self._extract_arguments(doc, action_id, context)
        
        # 3. Create the command structure
        command_structure = {
            'action': action_id,
            'args': entity_data['formatted_args'],
            'entities': entity_data['raw_entities'],
            'original_text': text
        }
        
        # 4. Update command history
        self.history.add_command(command_structure)
        
        # 5. Update learning data
        self._update_command_frequency(action_id)
        self._save_learning_data()
        
        return command_structure
    
    def _check_learning_data(self, text: str) -> Optional[str]:
        """Check if this input is similar to previously learned corrections"""
        if not self.learning_data["user_corrections"]:
            return None
        
        # Check for similar inputs that were corrected
        for original_input, correct_action in self.learning_data["user_corrections"].items():
            similarity = fuzz.ratio(text.lower(), original_input.lower())
            if similarity > 90:  # High similarity threshold
                return correct_action
        
        return None
    
    def _update_command_frequency(self, action_id: str) -> None:
        """Update the frequency count for this action"""
        if action_id not in self.learning_data["command_frequencies"]:
            self.learning_data["command_frequencies"][action_id] = 0
        
        self.learning_data["command_frequencies"][action_id] += 1
    
    def record_feedback(self, command_text: str, was_correct: bool, correct_action: str = None) -> None:
        """Record user feedback about a parse to improve future parsing"""
        if was_correct:
            self.learning_data["successful_parses"][command_text] = True
        else:
            self.learning_data["misinterpreted_commands"].append(command_text)
            if correct_action:
                self.learning_data["user_corrections"][command_text] = correct_action
        
        self._save_learning_data()


# Usage example
if __name__ == "__main__":
    parser = EnhancedParser()
    
    # Example parsing
    result = parser.parse_input("show me all files")
    print(result)
    
    # With context
    result = parser.parse_input("now change to that directory")
    print(result)
    
    # Record feedback
    parser.record_feedback("rename file.txt to newfile.txt", True)