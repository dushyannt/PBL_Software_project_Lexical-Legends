"""
File: command_pipeline.py
Description: Implementation of command pipelines to support complex sequences
             of operations in natural language.
"""

import re
import subprocess
from typing import List, Dict, Any, Optional, Tuple
import tempfile
import os
import json

class PipelineStage:
    """Represents a single stage in a command pipeline"""
    
    def __init__(self, action: str, args: List[str], original_text: str = None):
        self.action = action
        self.args = args
        self.original_text = original_text
        
    def __repr__(self):
        return f"PipelineStage(action='{self.action}', args={self.args})"


class CommandPipeline:
    """
    Handles the parsing and execution of command pipelines.
    Supports pipeline operations like:
    - "Find all Python files and count the lines"
    - "Show memory usage and save to stats.txt"
    - "List files, filter by txt, and sort by size"
    """
    
    def __init__(self, parser, executor):
        self.parser = parser
        self.executor = executor
        
        # Pipeline indicators in natural language
        self.pipeline_indicators = [
            r'\band\b', r'\bthen\b', r'\bafter that\b', r'\bnext\b',
            r'\bpipe to\b', r'\bpipe into\b', r'\bsend to\b', r'\bpass to\b',
            r'\bfollow(?:ed)? by\b', r'\bwith the result\b'
        ]
        self.pipeline_pattern = re.compile('|'.join(self.pipeline_indicators), re.IGNORECASE)
    
    def detect_pipeline(self, text: str) -> bool:
        """Detect if the text contains pipeline indicators"""
        return bool(self.pipeline_pattern.search(text))
    
    def split_pipeline_stages(self, text: str) -> List[str]:
        """Split the input text into separate pipeline stages"""
        # Replace pipeline indicators with a special token
        special_token = "###PIPELINE_SPLIT###"
        for indicator in self.pipeline_indicators:
            pattern = re.compile(indicator, re.IGNORECASE)
            text = pattern.sub(special_token, text)
            
        # Split by the special token
        stages = [stage.strip() for stage in text.split(special_token)]
        
        # Filter out empty stages
        return [stage for stage in stages if stage]
    
    def parse_pipeline(self, text: str) -> List[PipelineStage]:
        """
        Parse the text into a sequence of pipeline stages,
        each with its own action and arguments.
        """
        # Check if this looks like a pipeline
        if not self.detect_pipeline(text):
            # If not, treat as a single command
            cmd = self.parser.parse_input(text)
            if cmd and 'action' in cmd:
                return [PipelineStage(cmd['action'], cmd.get('args', []), text)]
            return []
            
        # Split into stages
        stage_texts = self.split_pipeline_stages(text)
        
        # Parse each stage
        pipeline = []
        for stage_text in stage_texts:
            cmd = self.parser.parse_input(stage_text)
            if cmd and 'action' in cmd and cmd['action'] not in ['unrecognized', 'suggest', 'error']:
                pipeline.append(PipelineStage(
                    cmd['action'],
                    cmd.get('args', []),
                    stage_text
                ))
            
        return pipeline
    
    def execute_pipeline(self, pipeline: List[PipelineStage]) -> Dict[str, Any]:
        """
        Execute a pipeline of commands, passing the output of each stage
        to the input of the next stage.
        """
        if not pipeline:
            return {
                'success': False,
                'error': 'Empty pipeline',
                'stdout': '',
                'stderr': 'No commands to execute',
                'stages_executed': 0
            }
            
        # If only one stage, execute directly
        if len(pipeline) == 1:
            stage = pipeline[0]
            cmd = {'action': stage.action, 'args': stage.args}
            return self._execute_single_command(cmd)
            
        # For multiple stages, we need to handle the pipeline
        return self._execute_multi_stage_pipeline(pipeline)
    
    def _execute_single_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single command and return the results"""
        try:
            # Delegate to the executor
            result = self.executor(cmd)
            
            # Create a standardized result structure
            # (Assumes executor returns some form of result that can be adapted)
            if isinstance(result, dict):
                return {
                    'success': result.get('returncode', 0) == 0,
                    'stdout': result.get('stdout', ''),
                    'stderr': result.get('stderr', ''),
                    'returncode': result.get('returncode', 0),
                    'stages_executed': 1
                }
            elif result is None or isinstance(result, str) and result.startswith('PYTHON_HANDLED'):
                # Handle internal Python execution
                return {
                    'success': True,
                    'stdout': 'Command executed successfully',
                    'stderr': '',
                    'returncode': 0,
                    'stages_executed': 1
                }
            else:
                # Unknown result format
                return {
                    'success': True,  # Assume success if we can't determine
                    'stdout': str(result) if result else '',
                    'stderr': '',
                    'returncode': 0,
                    'stages_executed': 1
                }
                
        except Exception as e:
            # Handle execution errors
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': f'Error executing command: {e}',
                'returncode': 1,
                'stages_executed': 0
            }
    
    def _execute_multi_stage_pipeline(self, pipeline: List[PipelineStage]) -> Dict[str, Any]:
        """Execute a multi-stage pipeline, passing output between stages"""
        stages_executed = 0
        current_input = None
        
        # We'll use temporary files for passing data between stages
        temp_files = []
        
        try:
            for i, stage in enumerate(pipeline):
                is_last_stage = i == len(pipeline) - 1
                
                # Maps the stage to a native command if possible
                native_cmd = self._map_to_native_command(stage, current_input, is_last_stage)
                
                if native_cmd:
                    # Execute the native command
                    result = self._execute_native_command(native_cmd, current_input)
                    
                    # Update for next stage
                    current_input = result.get('stdout', '')
                    stages_executed += 1
                    
                    # If the stage failed, stop the pipeline
                    if not result['success']:
                        return {
                            'success': False,
                            'stdout': current_input,
                            'stderr': result.get('stderr', ''),
                            'returncode': result.get('returncode', 1),
                            'stages_executed': stages_executed,
                            'failed_stage': i
                        }
                        
                else:
                    # If we can't map to a native command, try to use our executor
                    # Create a temp file for the input if needed
                    if current_input is not None:
                        input_file = tempfile.NamedTemporaryFile(delete=False)
                        input_file.write(current_input.encode('utf-8'))
                        input_file.close()
                        temp_files.append(input_file.name)
                        
                        # Add the input file to the args if appropriate
                        if stage.action in ['display_file', 'cat']:
                            stage.args = [input_file.name]
                    
                    # Execute the command
                    cmd = {'action': stage.action, 'args': stage.args}
                    result = self._execute_single_command(cmd)
                    
                    # Update for next stage
                    current_input = result.get('stdout', '')
                    stages_executed += 1
                    
                    # If the stage failed, stop the pipeline
                    if not result['success']:
                        return {
                            'success': False,
                            'stdout': current_input,
                            'stderr': result.get('stderr', ''),
                            'returncode': result.get('returncode', 1),
                            'stages_executed': stages_executed,
                            'failed_stage': i
                        }
            
            # All stages executed successfully
            return {
                'success': True,
                'stdout': current_input or '',
                'stderr': '',
                'returncode': 0,
                'stages_executed': stages_executed
            }
            
        finally:
            # Clean up temp files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
    
    def _map_to_native_command(self, stage: PipelineStage, 
                               input_data: Optional[str] = None,
                               is_last_stage: bool = False) -> Optional[List[str]]:
        """
        Map a pipeline stage to a native command that can be executed
        directly by subprocess, if possible.
        
        Returns None if the stage cannot be mapped to a native command.
        """
        # This is a simplified example - in a real implementation,
        # you would handle many more commands and OS-specific mappings
        
        action = stage.action
        args = stage.args
        
        if action == 'list_files':
            return ['ls', '-la'] if args else ['ls']
            
        elif action == 'display_file' and args:
            return ['cat'] + args
            
        elif action == 'grep' or action == 'find_text':
            if args:
                return ['grep'] + args
                
        elif action == 'count_lines':
            return ['wc', '-l']
            
        elif action == 'sort_lines':
            return ['sort'] + args
            
        # No native mapping available
        return None
    
    def _execute_native_command(self, cmd: List[str], input_data: Optional[str] = None) -> Dict[str, Any]:
        """Execute a native command using subprocess"""
        try:
            # Execute the command
            process = subprocess.run(
                cmd,
                input=input_data.encode('utf-8') if input_data else None,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Return the results
            return {
                'success': process.returncode == 0,
                'stdout': process.stdout,
                'stderr': process.stderr,
                'returncode': process.returncode
            }
            
        except Exception as e:
            # Handle execution errors
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': f'Error executing command: {e}',
                'returncode': 1
            }


class PipelineDetector:
    """
    Helper class to detect if a natural language input likely contains
    a pipeline or complex command that should be handled by the pipeline system.
    """
    
    def __init__(self):
        # Common pipeline phrases and structures
        self.pipeline_patterns = [
            r'\band\s+(?:then)?\s*(?:(?:show|display|list|find|count|sort))',
            r'(?:after|then|next)\s+(?:(?:show|display|list|find|count|sort))',
            r'(?:pipe|send|pass)\s+(?:to|into)',
            r'followed\s+by',
            r'with\s+the\s+result'
        ]
        
        # Complex action indicators
        self.complex_action_words = [
            'find', 'search', 'filter', 'count', 'sort', 'analyze',
            'organize', 'categorize', 'group', 'aggregate'
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.pipeline_patterns]
    
    def is_pipeline(self, text: str) -> bool:
        """Determine if the input text likely contains a pipeline"""
        # Check for explicit pipeline patterns
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return True
                
        # Count action words - multiple actions might indicate a pipeline
        action_count = sum(1 for word in self.complex_action_words if re.search(r'\b' + word + r'\b', text, re.IGNORECASE))
        if action_count >= 2:
            return True
            
        # If there are multiple distinct parts separated by commas,
        # it might be implicitly describing a pipeline
        parts = [p.strip() for p in text.split(',')]
        if len(parts) >= 3:  # At least 3 parts to be considered a pipeline
            # Check if each part could be a command
            action_patterns = [r'\b(?:list|show|find|get|display|count|sort)\b', r'\bfiles\b', r'\btext\b']
            compiled_action_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in action_patterns]
            
            action_parts = 0
            for part in parts:
                if any(pattern.search(part) for pattern in compiled_action_patterns):
                    action_parts += 1
                    
            return action_parts >= 2
        
        return False


class PipelineExamples:
    """
    Provides examples of pipeline commands for user help and training.
    """
    
    @staticmethod
    def get_examples() -> Dict[str, List[str]]:
        """Get examples of pipeline commands by category"""
        return {
            "File operations": [
                "Find all Python files and count the lines",
                "List files, filter by txt, and sort by size",
                "Search for 'error' in all log files and save results to errors.txt"
            ],
            "System monitoring": [
                "Show memory usage, sort by highest usage first, and display the top 5 processes",
                "Check disk space and create a report file"
            ],
            "Text processing": [
                "Display README.md and count the number of lines",
                "Find all TODOs in the code and create a summary",
                "Search for 'function' in all Python files, count occurrences, and sort by count"
            ],
            "Development tools": [
                "Run tests, capture failures, and create a report",
                "List git commits from last week and extract author statistics"
            ]
        }
    
    @staticmethod
    def get_random_example() -> str:
        """Get a random pipeline example for suggestion to the user"""
        import random
        
        examples = PipelineExamples.get_examples()
        category = random.choice(list(examples.keys()))
        return random.choice(examples[category])


# Usage example
if __name__ == "__main__":
    # This would normally be imported from your project
    class DummyParser:
        def parse_input(self, text):
            # Simplified dummy parser for demonstration
            if "list" in text or "show files" in text:
                return {'action': 'list_files', 'args': []}
            elif "count" in text:
                return {'action': 'count_lines', 'args': []}
            return None
    
    def dummy_executor(cmd):
        # Simplified dummy executor for demonstration
        return {'stdout': f"Executed {cmd['action']} with args {cmd['args']}", 'returncode': 0}
    
    # Create a pipeline with dummy components
    pipeline = CommandPipeline(DummyParser(), dummy_executor)
    
    # Test a pipeline command
    result = pipeline.parse_pipeline("list files and count lines")
    print("Parsed pipeline:", result)
    
    # Test pipeline detection
    detector = PipelineDetector()
    test_inputs = [
        "list files",
        "list files and count lines",
        "show all Python files, sort by size, and display the top 5",
        "check memory usage",
        "find errors in logs, save to report.txt, then email to admin"
    ]
    
    for input_text in test_inputs:
        is_pipeline = detector.is_pipeline(input_text)
        print(f"Input: '{input_text}' => Pipeline: {is_pipeline}")