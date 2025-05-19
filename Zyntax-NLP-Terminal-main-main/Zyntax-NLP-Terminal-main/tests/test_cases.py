"""
File: test_cases.py
Description: Contains test functions and test cases for validating the correctness
             of NLP parsing and system command execution.
Date Created: 05-04-2025
Last Updated: 05-04-2025
"""
"""
File: test_cases.py
Description: Comprehensive test suite for Zyntax NLP Terminal
             including tests for the parser, pipeline, and interface components.
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Import components to test
from nlp_engine.parser import parse_input, extract_relevant_entities
from nlp_engine.enhanced_parser import EnhancedParser
from nlp_engine.command_pipeline import CommandPipeline, PipelineStage, PipelineDetector
from interface.enhanced_interface import ZyntaxInterface
from command_executor.executor import execute_command, get_platform_command

class TestBasicParser(unittest.TestCase):
    """Tests for the original parser implementation"""
    
    def test_action_recognition(self):
        """Test that basic commands are recognized correctly"""
        test_cases = [
            ("list files", "list_files"),
            ("show me all files", "list_files"),
            ("ls", "list_files"),
            ("show current directory", "show_path"),
            ("pwd", "show_path"),
            ("make a new directory called test", "make_directory"),
            ("create file test.py", "create_file"),
            ("show the content of file.txt", "display_file"),
            ("check git status", "git_status"),
        ]
        
        for input_text, expected_action in test_cases:
            result = parse_input(input_text)
            self.assertIsNotNone(result, f"Parser returned None for '{input_text}'")
            self.assertEqual(result.get('action'), expected_action, 
                             f"Expected action '{expected_action}' for input '{input_text}', but got '{result.get('action')}'")
    
    def test_entity_extraction(self):
        """Test extraction of file names and paths"""
        import spacy
        nlp = spacy.load("en_core_web_sm")
        
        test_cases = [
            ("create file test.py", ["test.py"]),
            ("make directory project/src", ["project/src"]),
            ("delete file old_data.txt", ["old_data.txt"]),
            ("show content of README.md", ["README.md"]),
            ("move file.txt to backup/file.bak", ["file.txt", "backup/file.bak"]),
        ]
        
        for input_text, expected_entities in test_cases:
            doc = nlp(input_text)
            extracted = extract_relevant_entities(doc, input_text)
            self.assertEqual(extracted, expected_entities, 
                             f"Expected entities {expected_entities} for input '{input_text}', but got {extracted}")
    
    def test_suggestions(self):
        """Test suggestion mechanism for ambiguous commands"""
        # Test cases where the command should be suggested rather than executed directly
        test_cases = [
            ("lst files", "list_files"),  # Typo
            ("shoe files", "show_files"),  # Typo
            ("create folder", "make_directory"),  # Alternative phrasing
            ("remove file", "delete_file"),  # Alternative phrasing
        ]
        
        for input_text, expected_suggestion in test_cases:
            result = parse_input(input_text)
            self.assertEqual(result.get('action'), 'suggest', 
                             f"Expected 'suggest' action for input '{input_text}', but got '{result.get('action')}'")
            self.assertEqual(result.get('suggestion_action_id'), expected_suggestion, 
                             f"Expected suggestion '{expected_suggestion}' for input '{input_text}', but got '{result.get('suggestion_action_id')}'")


class TestEnhancedParser(unittest.TestCase):
    """Tests for the enhanced parser implementation"""
    
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.parser = EnhancedParser()
    
    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_context_awareness(self):
        """Test that the parser can use context from previous commands"""
        # First command creates a file
        cmd1 = self.parser.parse_input("create a file called test.txt")
        self.assertEqual(cmd1.get('action'), 'create_file')
        self.assertEqual(cmd1.get('args'), ['test.txt'])
        
        # Second command refers to "that file"
        cmd2 = self.parser.parse_input("display that file")
        self.assertEqual(cmd2.get('action'), 'display_file')
        self.assertEqual(cmd2.get('args'), ['test.txt'])
    
    def test_learning(self):
        """Test the learning capabilities of the enhanced parser"""
        # Record a correction
        self.parser.record_feedback("shoe me files", False, "list_files")
        
        # Now similar command should be recognized correctly
        cmd = self.parser.parse_input("shoe me files")
        self.assertEqual(cmd.get('action'), 'list_files')
    
    def test_specialized_entity_extraction(self):
        """Test extraction of specialized entities like file paths"""
        cmd = self.parser.parse_input("find text in /var/log/system.log")
        entities = cmd.get('entities', {})
        self.assertIn('file_paths', entities)
        self.assertIn('/var/log/system.log', entities['file_paths'])


class TestCommandPipeline(unittest.TestCase):
    """Tests for the command pipeline implementation"""
    
    def setUp(self):
        # Mock dependencies
        self.mock_parser = MagicMock()
        self.mock_executor = MagicMock()
        
        self.pipeline = CommandPipeline(self.mock_parser, self.mock_executor)
    
    def test_pipeline_detection(self):
        """Test detection of pipeline commands"""
        detector = PipelineDetector()
        
        # Should be detected as pipelines
        pipeline_inputs = [
            "list files and count lines",
            "find all Python files then sort by size",
            "show memory usage, filter by chrome, and display top 5",
            "search for 'error' in logs and save to report.txt"
        ]
        
        for input_text in pipeline_inputs:
            self.assertTrue(detector.is_pipeline(input_text), 
                           f"'{input_text}' should be detected as a pipeline")
        
        # Should not be detected as pipelines
        non_pipeline_inputs = [
            "list files",
            "show memory usage",
            "create file test.py",
            "change to documents directory"
        ]
        
        for input_text in non_pipeline_inputs:
            self.assertFalse(detector.is_pipeline(input_text), 
                            f"'{input_text}' should not be detected as a pipeline")
    
    def test_pipeline_parsing(self):
        """Test parsing of pipeline commands into stages"""
        # Set up mock parser to return expected values
        def mock_parse_input(text):
            if "list files" in text.lower():
                return {'action': 'list_files', 'args': []}
            elif "count lines" in text.lower():
                return {'action': 'count_lines', 'args': []}
            elif "sort" in text.lower():
                return {'action': 'sort_lines', 'args': ['-n']}
            return {'action': 'unrecognized'}
        
        self.mock_parser.parse_input.side_effect = mock_parse_input
        
        # Test multi-stage pipeline
        pipeline = self.pipeline.parse_pipeline("list files and count lines and sort numerically")
        
        self.assertEqual(len(pipeline), 3, "Pipeline should have 3 stages")
        self.assertEqual(pipeline[0].action, 'list_files')
        self.assertEqual(pipeline[1].action, 'count_lines')
        self.assertEqual(pipeline[2].action, 'sort_lines')
    
    def test_pipeline_execution(self):
        """Test execution of a pipeline"""
        # Create a simple two-stage pipeline
        pipeline = [
            PipelineStage('list_files', [], "list files"),
            PipelineStage('count_lines', [], "count lines")
        ]
        
        # Set up mock executor to return expected values
        def mock_execute(cmd):
            if cmd['action'] == 'list_files':
                return {'success': True, 'stdout': 'file1.txt\nfile2.txt\nfile3.txt\n', 'returncode': 0}
            elif cmd['action'] == 'count_lines':
                return {'success': True, 'stdout': '3', 'returncode': 0}
            return {'success': False, 'stderr': 'Unknown command', 'returncode': 1}
        
        self.mock_executor.side_effect = mock_execute
        
        # Execute the pipeline
        result = self.pipeline._execute_multi_stage_pipeline(pipeline)
        
        self.assertTrue(result['success'], "Pipeline execution should succeed")
        self.assertEqual(result['stdout'], '3', "Final output should be the count of lines")
        self.assertEqual(result['stages_executed'], 2, "Both stages should be executed")


class TestInterface(unittest.TestCase):
    """Tests for the enhanced interface"""
    
    def setUp(self):
        # Patch rich.console to prevent actual console output during tests
        self.console_patcher = patch('rich.console.Console')
        self.mock_console = self.console_patcher.start()
        
        # Create interface with patched console
        self.interface = ZyntaxInterface()
        self.interface.console = MagicMock()
    
    def tearDown(self):
        self.console_patcher.stop()
    
    def test_display_command_preview(self):
        """Test command preview display"""
        # Normal command
        cmd = {'action': 'list_files', 'args': []}
        self.interface.display_command_preview(cmd)
        self.interface.console.print.assert_called()
        
        # Destructive command
        self.interface.console.reset_mock()
        cmd = {'action': 'delete_file', 'args': ['important.txt']}
        self.interface.display_command_preview(cmd)
        # Should print with warning styling
        self.interface.console.print.assert_called()
        # The first positional arg should be a Panel
        call_args = self.interface.console.print.call_args[0]
        self.assertTrue(len(call_args) > 0, "Console.print should be called with arguments")
    
    def test_settings_command(self):
        """Test handling of settings commands"""
        # Test verbose setting
        result = self.interface.handle_settings_command("verbose on")
        self.assertTrue(result, "Settings command should be handled")
        self.assertTrue(self.interface.verbose, "Verbose mode should be turned on")
        
        # Test preview setting
        result = self.interface.handle_settings_command("preview off")
        self.assertTrue(result, "Settings command should be handled")
        self.assertFalse(self.interface.show_command_preview, "Command previews should be turned off")
        
        # Test invalid settings command
        result = self.interface.handle_settings_command("invalid setting")
        self.assertFalse(result, "Invalid settings command should not be handled")


class TestCommandExecution(unittest.TestCase):
    """Tests for command execution functionality"""
    
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.old_dir = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        # Clean up temporary directory
        os.chdir(self.old_dir)
        shutil.rmtree(self.test_dir)
    
    def test_get_platform_command(self):
        """Test platform-specific command mapping"""
        # Test 'list_files' command
        cmd = get_platform_command('list_files', [])
        # Command should be a list suitable for subprocess
        self.assertIsInstance(cmd, list, "Command should be a list")
        
        # Test 'change_directory' command (should be handled internally)
        cmd = get_platform_command('change_directory', [self.test_dir])
        self.assertIsInstance(cmd, str, "Command should be a string indicating internal handling")
        self.assertTrue(cmd.startswith("PYTHON_HANDLED"), "Should use internal Python handler for cd")
    
    @patch('subprocess.run')
    def test_execute_command(self, mock_run):
        """Test command execution"""
        # Mock subprocess.run to return a successful result
        mock_process = MagicMock()
        mock_process.stdout = "mocked output"
        mock_process.stderr = ""
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Test a simple command
        cmd = {'action': 'list_files', 'args': []}
        execute_command(cmd)
        
        # subprocess.run should be called with the appropriate command
        mock_run.assert_called_once()
        # First arg to run should be the command list
        cmd_list = mock_run.call_args[0][0]
        self.assertIsInstance(cmd_list, list, "Command should be a list")
        
        # Test a command that's handled internally
        mock_run.reset_mock()
        cmd = {'action': 'memory_usage', 'args': []}
        execute_command(cmd)
        
        # subprocess.run should not be called for internal commands
        mock_run.assert_not_called()


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    @patch('subprocess.run')
    def test_basic_workflow(self, mock_run):
        """Test a basic workflow of commands"""
        # Mock subprocess.run to return successful results
        mock_process = MagicMock()
        mock_process.stdout = "mocked output"
        mock_process.stderr = ""
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Create the parser
        parser = EnhancedParser()
        
        # Test a sequence of related commands
        cmds = [
            "list files",
            "create file test.py",
            "show content of test.py",
            "check git status"
        ]
        
        for cmd_text in cmds:
            # Parse the command
            parsed_cmd = parser.parse_input(cmd_text)
            
            # Make sure it's recognized
            self.assertNotEqual(parsed_cmd.get('action'), 'unrecognized', 
                               f"Command '{cmd_text}' should be recognized")
            
            # Execute the command
            execute_command({
                'action': parsed_cmd.get('action'),
                'args': parsed_cmd.get('args', [])
            })
    
    def test_pipeline_workflow(self):
        """Test a workflow using pipelines"""
        # Create mocks
        mock_parser = MagicMock()
        mock_executor = MagicMock()
        
        # Configure mock parser
        def mock_parse_input(text):
            if "list files" in text.lower():
                return {'action': 'list_files', 'args': []}
            elif "filter" in text.lower():
                return {'action': 'grep', 'args': ['.py']}
            elif "count" in text.lower():
                return {'action': 'count_lines', 'args': []}
            return {'action': 'unrecognized'}
        
        mock_parser.parse_input.side_effect = mock_parse_input
        
        # Configure mock executor to simulate output passing
        def mock_execute(cmd):
            if cmd['action'] == 'list_files':
                return {'success': True, 'stdout': 'file1.py\nfile2.txt\nfile3.py\n', 'returncode': 0}
            elif cmd['action'] == 'grep':
                # Filter input to only show .py files
                lines = cmd.get('_input', '').split('\n')
                filtered = [line for line in lines if '.py' in line]
                return {'success': True, 'stdout': '\n'.join(filtered), 'returncode': 0}
            elif cmd['action'] == 'count_lines':
                lines = cmd.get('_input', '').split('\n')
                count = len([l for l in lines if l.strip()])
                return {'success': True, 'stdout': str(count), 'returncode': 0}
            return {'success': False, 'stderr': 'Unknown command', 'returncode': 1}
        
        mock_executor.side_effect = mock_execute
        
        # Create the pipeline
        pipeline = CommandPipeline(mock_parser, mock_executor)
        
        # Parse and execute a pipeline command
        pipeline_text = "list files, filter Python files, and count them"
        stages = pipeline.parse_pipeline(pipeline_text)
        
        # Should find all three stages
        self.assertEqual(len(stages), 3, f"Pipeline '{pipeline_text}' should have 3 stages")
        
        # Execute the pipeline (would need to modify _execute_multi_stage_pipeline to work with our mocks)
        # For now, just check that the stages are correctly identified
        self.assertEqual(stages[0].action, 'list_files')
        self.assertEqual(stages[1].action, 'grep')
        self.assertEqual(stages[2].action, 'count_lines')


if __name__ == "__main__":
    unittest.main()