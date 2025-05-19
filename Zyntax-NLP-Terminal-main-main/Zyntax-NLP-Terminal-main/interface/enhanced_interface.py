"""
File: enhanced_interface.py
Description: An improved terminal interface for Zyntax with rich formatting,
             command previews, and learning feedback.
"""

import os
import sys
import platform
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from typing import Dict, List, Optional, Any

class ZyntaxInterface:
    """
    Enhanced terminal interface for Zyntax using Rich for
    better visualization and user interaction.
    """
    
    def __init__(self, verbose: bool = False):
        # Initialize Rich console
        self.console = Console()
        self.verbose = verbose
        self.last_command = None
        self.show_command_preview = True
        
        # Theme colors
        self.colors = {
            'primary': 'cyan',
            'secondary': 'green',
            'warning': 'yellow',
            'error': 'red',
            'success': 'green'
        }
    
    def display_welcome(self) -> None:
        """Display the welcome message and initial help"""
        header_text = Text()
        header_text.append("🧠 Welcome to ", style="bold")
        header_text.append("ZYNTAX", style=f"bold {self.colors['primary']}")
        header_text.append(" - Your NLP-powered Terminal!", style="bold")
        
        self.console.print(Panel(header_text, expand=False))
        self.console.print("Type commands in natural language or [bold]'help'[/bold] to see examples.")
        self.console.print("Type [bold]'exit'[/bold] or [bold]'quit'[/bold] to leave.\n")
        
        if self.verbose:
            self.display_quick_help()
    
    def display_quick_help(self) -> None:
        """Display a quick help guide with examples"""
        examples = [
            ("List files", "show me all files in this directory"),
            ("Change directory", "change to the src folder"),
            ("Create file", "create a new file called config.json"),
            ("Display file", "show the content of README.md"),
            ("Git operations", "check git status"),
            ("System info", "show memory usage")
        ]
        
        table = Table(title="Example Commands")
        table.add_column("Action", style=self.colors['secondary'])
        table.add_column("Example Phrase", style="white")
        
        for action, example in examples:
            table.add_row(action, example)
        
        self.console.print(table)
        self.console.print()
    
    def get_input(self) -> str:
        """Get user input with styled prompt"""
        prompt_style = f"bold {self.colors['primary']}"
        return Prompt.ask(f"[{prompt_style}]Zyntax>")
    
    def display_command_preview(self, command: Dict) -> None:
        """Display a preview of the command that will be executed"""
        if not self.show_command_preview:
            return
            
        action = command.get('action')
        args = command.get('args', [])
        
        # Skip for certain actions
        if action in ['unrecognized', 'suggest', 'error']:
            return
            
        # For destructive commands, emphasize the preview
        is_destructive = action in ['delete_file', 'delete_directory', 'git_reset']
        style = self.colors['warning'] if is_destructive else self.colors['secondary']
        
        panel_title = "⚠️ Destructive Command" if is_destructive else "Command Preview"
        
        # Format the command preview
        preview_text = Text()
        preview_text.append(f"Action: ", style="bold")
        preview_text.append(action, style=style)
        preview_text.append("\nArguments: ", style="bold")
        
        if args:
            preview_text.append(", ".join(repr(arg) for arg in args), style=style)
        else:
            preview_text.append("None", style="italic")
            
        # Add native command equivalent if available
        if hasattr(self, 'get_native_command'):
            native_cmd = self.get_native_command(action, args)
            if native_cmd:
                preview_text.append("\nNative equivalent: ", style="bold")
                preview_text.append(native_cmd, style=style)
                
        self.console.print(Panel(preview_text, title=panel_title, border_style=style))
        
        # For destructive commands, ask for confirmation
        if is_destructive:
            return Confirm.ask("Proceed with this command?", default=False)
        
        return True
    
    def display_execution_results(self, 
                                  stdout: str = None, 
                                  stderr: str = None, 
                                  return_code: int = 0,
                                  command_type: str = None) -> None:
        """Display execution results with proper formatting"""
        if stdout:
            if command_type == 'file_content' and len(stdout) > 0:
                # Attempt to detect file type for syntax highlighting
                file_extension = self.last_command.get('args', [''])[0].split('.')[-1].lower()
                lexer = self._get_lexer_for_extension(file_extension)
                
                # Show with syntax highlighting if we have a lexer
                if lexer:
                    self.console.print(Syntax(stdout, lexer, theme="monokai"))
                else:
                    self.console.print(Panel(stdout, title="File Content"))
            else:
                self.console.print(Panel(stdout, title="Output", border_style=self.colors['success']))
                
        if stderr:
            self.console.print(Panel(stderr, title="Errors", border_style=self.colors['error']))
            
        if return_code != 0:
            self.console.print(f"[{self.colors['warning']}]⚠️ Command exited with code: {return_code}[/]")
    
    def _get_lexer_for_extension(self, extension: str) -> Optional[str]:
        """Get the appropriate lexer for syntax highlighting based on file extension"""
        extension_map = {
            'py': 'python',
            'js': 'javascript',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'md': 'markdown',
            'txt': 'text',
            'sh': 'bash',
            'bat': 'batch',
            'ps1': 'powershell',
            'sql': 'sql',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml'
        }
        return extension_map.get(extension.lower())
    
    def display_error(self, message: str) -> None:
        """Display an error message"""
        self.console.print(f"[{self.colors['error']}]❌ {message}[/]")
    
    def display_warning(self, message: str) -> None:
        """Display a warning message"""
        self.console.print(f"[{self.colors['warning']}]⚠️ {message}[/]")
    
    def display_success(self, message: str) -> None:
        """Display a success message"""
        self.console.print(f"[{self.colors['success']}]✅ {message}[/]")
    
    def display_suggestion(self, suggestion: str, action_id: str) -> bool:
        """Display a command suggestion and ask for confirmation"""
        self.console.print(Panel(
            f"Did you mean: [bold]{suggestion}[/bold]?",
            title="Suggestion",
            border_style=self.colors['secondary']
        ))
        return Confirm.ask("Execute this command?", default=True)
    
    def request_feedback(self) -> Dict:
        """Request feedback about the executed command for learning"""
        self.console.print("\n[italic]Help Zyntax learn:[/italic]")
        was_correct = Confirm.ask("Did Zyntax understand your command correctly?", default=True)
        
        feedback = {"was_correct": was_correct}
        
        if not was_correct:
            # Ask what the user actually wanted
            self.console.print("What command were you trying to execute? (Select one or type a number)")
            
            # Display common alternatives
            alternatives = [
                "list_files", "display_file", "create_file", "delete_file",
                "change_directory", "make_directory", "delete_directory",
                "show_processes", "memory_usage", "git_status"
            ]
            
            for i, alt in enumerate(alternatives, 1):
                self.console.print(f"  {i}. {alt}")
                
            # Get their selection
            selection = Prompt.ask("Enter number or command name", default="skip")
            
            if selection.isdigit() and 1 <= int(selection) <= len(alternatives):
                feedback["correct_action"] = alternatives[int(selection) - 1]
            elif selection != "skip":
                feedback["correct_action"] = selection
                
        return feedback
    
    def display_help(self) -> None:
        """Display comprehensive help information"""
        help_text = """
        Zyntax understands natural language commands for common terminal operations.
        
        You can ask for things like:
        - "Show me all the files in this directory"
        - "Create a new file called test.py"
        - "Delete the logs folder"
        - "What's my current directory?"
        - "Check git status"
        - "How much memory is my system using?"
        
        Zyntax will translate these into the appropriate terminal commands.
        
        For more complex operations, you can be more specific:
        - "Copy config.json to backup/config.json.bak"
        - "Find all Python files with more than 100 lines"
        - "Commit changes with message 'Fixed bug in parser'"
        """
        
        self.console.print(Panel(help_text, title="Zyntax Help", border_style=self.colors['primary']))
        
        # Command reference
        table = Table(title="Supported Commands")
        table.add_column("Category", style="bold")
        table.add_column("Actions", style=self.colors['secondary'])
        table.add_column("Example Phrases", style="white")
        
        # File operations
        table.add_row(
            "File Operations",
            "list_files, create_file, delete_file, display_file, move_rename, copy_file",
            "show files, create file.txt, remove old.log, show content of README.md"
        )
        
        # Directory operations
        table.add_row(
            "Directory Operations",
            "show_path, change_directory, make_directory, delete_directory",
            "where am I, go to src folder, create new directory, remove empty folder"
        )
        
        # System operations
        table.add_row(
            "System Info",
            "whoami, show_processes, disk_usage, memory_usage",
            "who am I, show running processes, how much disk space, memory usage"
        )
        
        # Git operations
        table.add_row(
            "Git Operations",
            "git_status, git_init, git_commit",
            "check git status, initialize git, commit with message 'update'"
        )
        
        self.console.print(table)
        
        # Settings
        settings_table = Table(title="Settings")
        settings_table.add_column("Command", style="bold")
        settings_table.add_column("Description", style="white")
        
        settings_table.add_row(
            "verbose on/off",
            "Enable/disable verbose output with explanations"
        )
        settings_table.add_row(
            "preview on/off",
            "Enable/disable command previews before execution"
        )
        settings_table.add_row(
            "feedback on/off",
            "Enable/disable learning feedback requests"
        )
        
        self.console.print(settings_table)
    
    def handle_settings_command(self, command: str) -> bool:
        """Handle settings-related commands and return True if processed"""
        if command.startswith(("verbose", "preview", "feedback")):
            parts = command.split()
            if len(parts) == 2 and parts[1] in ["on", "off"]:
                setting = parts[0]
                value = parts[1] == "on"
                
                if setting == "verbose":
                    self.verbose = value
                    self.display_success(f"Verbose mode turned {'on' if value else 'off'}")
                elif setting == "preview":
                    self.show_command_preview = value
                    self.display_success(f"Command previews turned {'on' if value else 'off'}")
                elif setting == "feedback":
                    # Would set feedback setting
                    self.display_success(f"Learning feedback turned {'on' if value else 'off'}")
                    
                return True
                
        return False
    
    def display_goodbye(self) -> None:
        """Display a goodbye message"""
        self.console.print("\n[bold]👋 Thank you for using Zyntax! Have a great day![/bold]")


class AdvancedTerminal:
    """
    Top-level class that integrates the enhanced interface with the parser
    and command execution components.
    """
    
    def __init__(self, config_path: str = None):
        # Initialize components
        self.interface = ZyntaxInterface()
        
        # Import parser and executor here to avoid circular imports
        from nlp_engine.enhanced_parser import EnhancedParser
        from command_executor.executor import execute_command 
        
        self.parser = EnhancedParser(config_path)
        self.execute_command = execute_command
        
        # Settings
        self.learning_mode = True
        self.running = True
    
    def run(self):
        """Main terminal loop"""
        # Display welcome message
        self.interface.display_welcome()
        
        # Main loop
        while self.running:
            try:
                # Get user input
                user_input = self.interface.get_input()
                
                # Handle exit commands
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    self.running = False
                    break
                
                # Handle empty input
                if not user_input.strip():
                    continue
                
                # Handle help command
                if user_input.lower() == 'help':
                    self.interface.display_help()
                    continue
                
                # Handle settings commands
                if self.interface.handle_settings_command(user_input):
                    continue
                
                # Parse the input
                structured_command = self.parser.parse_input(user_input)
                
                # Store for reference
                self.interface.last_command = structured_command
                
                # Process the command based on action
                action = structured_command.get('action')
                
                if action == 'unrecognized':
                    self.interface.display_error("Command not recognized. Type 'help' for examples.")
                
                elif action == 'suggest':
                    # Handle suggestion
                    suggestion_phrase = structured_command.get('suggestion_phrase', 'that command')
                    suggestion_action_id = structured_command.get('suggestion_action_id')
                    
                    if not suggestion_action_id:
                        self.interface.display_error("Suggestion error: No action ID provided.")
                        continue
                    
                    # Ask for confirmation
                    if self.interface.display_suggestion(suggestion_phrase, suggestion_action_id):
                        # User accepted suggestion, extract entities and execute
                        from nlp_engine.parser import extract_relevant_entities
                        import spacy
                        
                        nlp = spacy.load("en_core_web_sm")
                        doc = nlp(user_input)
                        args = extract_relevant_entities(doc, user_input)
                        
                        confirmed_command = {
                            'action': suggestion_action_id,
                            'args': args
                        }
                        
                        # Show preview before execution
                        if self.interface.display_command_preview(confirmed_command):
                            self.execute_command(confirmed_command)
                    else:
                        self.interface.display_warning("Command cancelled.")
                
                elif action == 'error':
                    # Handle specific error
                    self.interface.display_error(structured_command.get('message', 'Parser error'))
                
                else:
                    # Preview and execute recognized command
                    if self.interface.display_command_preview(structured_command):
                        # Determine the command type for better output formatting
                        command_type = None
                        if action == 'display_file':
                            command_type = 'file_content'
                        
                        # Execute the command
                        result = self.execute_command(structured_command)
                        
                        # Display results (in a real implementation, extract stdout/stderr from result)
                        # This is a placeholder assuming execute_command returns appropriate data
                        if isinstance(result, dict):
                            self.interface.display_execution_results(
                                stdout=result.get('stdout'),
                                stderr=result.get('stderr'),
                                return_code=result.get('return_code', 0),
                                command_type=command_type
                            )
                        
                        # Request feedback for learning if enabled
                        if self.learning_mode:
                            feedback = self.interface.request_feedback()
                            if feedback:
                                self.parser.record_feedback(
                                    user_input,
                                    feedback['was_correct'],
                                    feedback.get('correct_action')
                                )
                
            except KeyboardInterrupt:
                # Handle Ctrl+C
                self.interface.console.print("\nOperation cancelled. Press Ctrl+C again to exit.")
                try:
                    # Wait for another Ctrl+C to exit
                    self.interface.get_input()
                except KeyboardInterrupt:
                    self.running = False
                    break
            
            except EOFError:
                # Handle Ctrl+D
                self.running = False
                break
            
            except Exception as e:
                # Handle unexpected errors
                self.interface.display_error(f"An unexpected error occurred: {e}")
                if self.interface.verbose:
                    import traceback
                    self.interface.console.print(Panel(traceback.format_exc(), title="Error Details", border_style="red"))
        
        # Display goodbye message
        self.interface.display_goodbye()


if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    arg_parser = argparse.ArgumentParser(description="Zyntax - NLP-powered Terminal")
    arg_parser.add_argument("--config", help="Path to configuration file")
    arg_parser.add_argument("--verbose", action="store_true", help="Enable verbose mode")
    args = arg_parser.parse_args()
    
    # Start the terminal
    terminal = AdvancedTerminal(config_path=args.config)
    if args.verbose:
        terminal.interface.verbose = True
    
    terminal.run()