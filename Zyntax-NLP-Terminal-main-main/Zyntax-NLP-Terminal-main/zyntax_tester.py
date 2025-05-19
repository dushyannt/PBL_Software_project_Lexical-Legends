"""
File: zyntax_tester.py
Description: A testing interface for Zyntax that visualizes the NLP processing,
             command execution, and provides feedback mechanisms. Built on top of
             the Rich library for beautiful terminal output.
"""

import sys
import os
import time
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich import box
from rich.markdown import Markdown

# Import Zyntax components
from nlp_engine.enhanced_parser import EnhancedParser
from nlp_engine.command_pipeline import CommandPipeline, PipelineDetector
from command_executor.executor import execute_command, get_platform_command
import platform


class ZyntaxTester:
    """
    Testing interface for Zyntax that visualizes NLP processing pipeline,
    command execution, and provides feedback mechanisms.
    """
    
    def __init__(self, config_path: str = None, debug: bool = False):
        # Initialize Rich console
        self.console = Console()
        
        # Set up components
        self.parser = EnhancedParser(config_path)
        self.pipeline_detector = PipelineDetector()
        self.debug = debug
        self.test_mode = False
        self.history: List[Dict] = []
        
        # Theme colors
        self.colors = {
            'primary': 'cyan',
            'secondary': 'green',
            'warning': 'yellow',
            'error': 'red',
            'success': 'green',
            'highlight': 'magenta',
            'muted': 'dim white'
        }
        
        # Layout setup
        self.layout = self._create_layout()
        
        # Settings
        self.execution_enabled = True
        self.show_command_preview = True
        self.collect_feedback = True
        self.auto_suggest = False
    
    def _create_layout(self) -> Layout:
        """Create the layout structure for the interface"""
        layout = Layout(name="root")
        
        # Split into main content and footer
        layout.split(
            Layout(name="main", ratio=9),
            Layout(name="footer", size=1)
        )
        
        # Split main into input/visualization and output sections
        layout["main"].split_row(
            Layout(name="visualization", ratio=1),
            Layout(name="output", ratio=1),
        )
        
        return layout
    
    def display_welcome(self) -> None:
        """Display the welcome message and initial info"""
        self.console.clear()
        title = Text()
        title.append("🧠 ", style="bold")
        title.append("ZYNTAX TESTING INTERFACE", style=f"bold {self.colors['primary']}")
        
        # Create welcome panel
        welcome_text = """
        Welcome to the Zyntax Testing Interface!
        
        This interface allows you to:
        • Test natural language commands
        • See how they're parsed and interpreted
        • View command execution previews
        • Provide feedback to improve the learning system
        
        Type [bold cyan]commands in natural language[/bold cyan] to test.
        Type [bold green]'help'[/bold green] for examples or [bold]'exit'[/bold] to quit.
        """
        
        welcome_panel = Panel(
            Markdown(welcome_text),
            title=title,
            border_style=self.colors['primary'],
            padding=(1, 2)
        )
        
        # Create settings panel and examples_panel first
        settings_table = Table(show_header=False, box=box.SIMPLE)
        settings_table.add_column("Setting", style=f"bold {self.colors['secondary']}")
        settings_table.add_column("Status", style="white")
        
        settings_table.add_row(
            "Command Execution",
            "✅ Enabled" if self.execution_enabled else "❌ Disabled"
        )
        settings_table.add_row(
            "Command Preview",
            "✅ Enabled" if self.show_command_preview else "❌ Disabled"
        )
        settings_table.add_row(
            "Feedback Collection",
            "✅ Enabled" if self.collect_feedback else "❌ Disabled"
        )
        settings_table.add_row(
            "Test Mode",
            "✅ Enabled" if self.test_mode else "❌ Disabled"
        )
        
        settings_panel = Panel(
            settings_table,
            title="Settings",
            border_style=self.colors['secondary'],
            padding=(1, 2)
        )
        
        example_cmd_text = """
        Example commands to try:
        • "list all files in this directory"
        • "create a file called test.py"
        • "show memory usage"
        • "find all python files and count the lines"
        • "change to the src directory then list files"
        """
        
        examples_panel = Panel(
            Markdown(example_cmd_text),
            title="Quick Examples",
            border_style=self.colors['highlight'],
            padding=(1, 2)
        )
        
        # Create a layout for the output content
        output_layout = Layout()
        output_layout.split(
            Layout(name="settings", size=10),
            Layout(name="examples")
        )
        
        # Update the layouts with their content
        output_layout["settings"].update(settings_panel)
        output_layout["examples"].update(examples_panel)
        
        # Update the main layout
        self.layout["visualization"].update(welcome_panel)
        self.layout["output"].update(Panel(
            output_layout,
            title="Information",
            border_style=self.colors['primary']
        ))
        
        # Display the layout
        self.console.print(self.layout)
    
    def get_input(self) -> str:
        """Get user input with styled prompt"""
        prompt_style = f"bold {self.colors['primary']}"
        return Prompt.ask(f"[{prompt_style}]Zyntax Test>")
    
    def handle_command(self, command: str) -> bool:
        """
        Handle a user command and display the results
        Returns True to continue, False to exit
        """
        if not command.strip():
            return True
        
        # Handle special commands
        if command.lower() == 'exit' or command.lower() == 'quit':
            return False
        
        if command.lower() == 'help':
            self.display_help()
            return True
        
        if command.lower() == 'clear' or command.lower() == 'cls':
            self.console.clear()
            self.display_welcome()
            return True
        
        # Handle settings commands
        if self._handle_settings_command(command):
            return True
        
        # Process the command
        self._process_command(command)
        return True
    
    def _handle_settings_command(self, command: str) -> bool:
        """Handle settings-related commands"""
        command = command.lower()
        
        if command == 'settings':
            self._display_settings()
            return True
        
        setting_commands = {
            'execution on': lambda: self._update_setting('execution_enabled', True),
            'execution off': lambda: self._update_setting('execution_enabled', False),
            'preview on': lambda: self._update_setting('show_command_preview', True),
            'preview off': lambda: self._update_setting('show_command_preview', False),
            'feedback on': lambda: self._update_setting('collect_feedback', True),
            'feedback off': lambda: self._update_setting('collect_feedback', False),
            'suggest on': lambda: self._update_setting('auto_suggest', True),
            'suggest off': lambda: self._update_setting('auto_suggest', False),
            'test mode on': lambda: self._update_setting('test_mode', True),
            'test mode off': lambda: self._update_setting('test_mode', False),
        }
        
        for cmd, action in setting_commands.items():
            if command == cmd:
                action()
                self._display_settings()
                return True
        
        return False
    
    def _update_setting(self, setting: str, value: bool) -> None:
        """Update a boolean setting"""
        if hasattr(self, setting):
            setattr(self, setting, value)
            self.console.print(f"[{self.colors['success']}]✓ {setting.replace('_', ' ').title()} {'enabled' if value else 'disabled'}[/]")
    
    def _display_settings(self) -> None:
        """Display current settings"""
        settings_table = Table(title="Current Settings")
        settings_table.add_column("Setting", style=f"bold {self.colors['secondary']}")
        settings_table.add_column("Status", style="white")
        settings_table.add_column("Command to Change", style=self.colors['muted'])
        
        settings = [
            ("Command Execution", self.execution_enabled, "execution on/off"),
            ("Command Preview", self.show_command_preview, "preview on/off"),
            ("Feedback Collection", self.collect_feedback, "feedback on/off"),
            ("Auto-Suggest", self.auto_suggest, "suggest on/off"),
            ("Test Mode", self.test_mode, "test mode on/off"),
        ]
        
        for name, enabled, command in settings:
            status = f"[{self.colors['success']}]✅ Enabled[/]" if enabled else f"[{self.colors['error']}]❌ Disabled[/]"
            settings_table.add_row(name, status, command)
        
        self.console.print(settings_table)
    
    def _process_command(self, command: str) -> None:
        """Process a natural language command and display the results"""
        # Clear screen for new command
        self.console.clear()
        
        # 1. Initial command display
        command_panel = Panel(
            Text(command, style="bold"),
            title="Natural Language Command",
            border_style=self.colors['primary'],
            padding=(1, 2)
        )
        
        # Spinner while processing
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]Processing command..."),
            transient=True,
        ) as progress:
            progress.add_task("processing", total=None)
            
            # Check if it's a pipeline command
            is_pipeline = self.pipeline_detector.is_pipeline(command)
            
            # Parse the command
            if is_pipeline:
                # Pipeline processing
                pipeline = CommandPipeline(self.parser, execute_command)
                stages = pipeline.parse_pipeline(command)
                parsed_info = {
                    'is_pipeline': True,
                    'stages': stages,
                    'original': command
                }
            else:
                # Single command processing
                parsed_command = self.parser.parse_input(command)
                parsed_info = {
                    'is_pipeline': False,
                    'command': parsed_command,
                    'original': command
                }
            
            # Add slight delay to make processing visible
            if self.debug:
                time.sleep(0.5)
        
        # 2. Visualization of parsing results
        if is_pipeline:
            viz_panel = self._create_pipeline_visualization(parsed_info)
        else:
            viz_panel = self._create_command_visualization(parsed_info)
        
        # 3. Command execution preview
        if self.show_command_preview:
            preview_panel = self._create_preview_panel(parsed_info)
        else:
            preview_panel = Panel(
                "Command preview disabled. Enable with 'preview on'",
                title="Command Preview",
                border_style=self.colors['muted'],
                padding=(1, 2)
            )
        
        # 4. Handle execution
        if self.execution_enabled and not self.test_mode:
            execution_panel = self._execute_command(parsed_info)
        else:
            execution_panel = Panel(
                "Execution disabled or in test mode",
                title="Execution Results",
                border_style=self.colors['muted'],
                padding=(1, 2)
            )
        
        # Update the layout
        viz_layout = Layout(name="viz_content")
        viz_layout.split(
            Layout(command_panel, name="command", size=3),
            Layout(viz_panel, name="parsing"),
            Layout(preview_panel, name="preview", size=8),
        )
        
        self.layout["visualization"].update(viz_layout)
        self.layout["output"].update(execution_panel)
        
        # Display the layout
        self.console.print(self.layout)
        
        # 5. Collect feedback if enabled
        if self.collect_feedback and not self.test_mode:
            self._collect_feedback(parsed_info)
        
        # Add to history
        self.history.append({
            'command': command,
            'parsed_info': parsed_info,
            'timestamp': time.time()
        })
    
    def _create_command_visualization(self, parsed_info: Dict) -> Panel:
        """Create visualization for a single command"""
        command = parsed_info['command']
        
        # Create table for visualization
        table = Table(show_header=True, box=box.ROUNDED)
        table.add_column("Property", style=f"bold {self.colors['secondary']}")
        table.add_column("Value", style="white")
        
        # Action
        action = command.get('action', 'unknown')
        action_style = self.colors['error'] if action in ['unrecognized', 'error', 'suggest'] else self.colors['success']
        table.add_row("Action", f"[{action_style}]{action}[/]")
        
        # Arguments
        args = command.get('args', [])
        args_text = "\n".join([f"• {arg}" for arg in args]) if args else "None"
        table.add_row("Arguments", args_text)
        
        # Entities (if available in enhanced parser)
        if 'entities' in command:
            entities = command['entities']
            entities_text = ""
            for entity_type, values in entities.items():
                if values:
                    entities_text += f"[bold]{entity_type}[/]: {', '.join(values)}\n"
            
            if entities_text:
                table.add_row("Extracted Entities", entities_text)
        
        # Suggestion (if applicable)
        if action == 'suggest':
            suggestion_phrase = command.get('suggestion_phrase', '')
            suggestion_id = command.get('suggestion_action_id', '')
            
            if suggestion_phrase and suggestion_id:
                table.add_row(
                    "Suggestion",
                    f"[{self.colors['highlight']}]Did you mean: '{suggestion_phrase}' ({suggestion_id})?[/]"
                )
                
                if self.auto_suggest:
                    # Auto-confirm suggestion
                    suggestion_command = {
                        'action': suggestion_id,
                        'args': command.get('args', [])
                    }
                    parsed_info['command'] = suggestion_command
                    table.add_row(
                        "Auto-Suggest",
                        f"[{self.colors['success']}]Automatically accepted suggestion[/]"
                    )
        
        # Error (if applicable)
        if action == 'error':
            error_message = command.get('message', 'Unknown error')
            table.add_row(
                "Error",
                f"[{self.colors['error']}]{error_message}[/]"
            )
        
        return Panel(
            table,
            title="Parsing Results",
            border_style=self.colors['secondary'],
            padding=(1, 2)
        )
    
    def _create_pipeline_visualization(self, parsed_info: Dict) -> Panel:
        """Create visualization for a pipeline command"""
        stages = parsed_info['stages']
        
        # Create table for pipeline stages
        table = Table(show_header=True, box=box.ROUNDED)
        table.add_column("#", style=f"bold {self.colors['muted']}")
        table.add_column("Stage", style=f"bold {self.colors['secondary']}")
        table.add_column("Action", style=f"bold {self.colors['highlight']}")
        table.add_column("Args", style="white")
        
        # Add each stage to the table
        for i, stage in enumerate(stages, 1):
            action = stage.action
            args = ", ".join(stage.args) if stage.args else "None"
            original_text = stage.original_text or "Unknown"
            
            table.add_row(
                str(i),
                original_text,
                action,
                args
            )
        
        # If no stages were found
        if not stages:
            table.add_row("N/A", "No pipeline stages detected", "N/A", "N/A")
        
        # Create pipeline flow diagram
        flow_text = Text()
        
        for i, stage in enumerate(stages):
            # Add stage
            flow_text.append(f"Stage {i+1}: ", style=f"bold {self.colors['muted']}")
            flow_text.append(stage.action, style=f"bold {self.colors['highlight']}")
            
            # Add arrow if not the last stage
            if i < len(stages) - 1:
                flow_text.append(" → ", style=f"bold {self.colors['primary']}")
        
        # Create a layout for the pipeline visualization
        pipeline_layout = Layout()
        pipeline_layout.split(
            Layout(table),
            Layout(Panel(
                flow_text,
                title="Pipeline Flow",
                border_style=self.colors['primary'],
                padding=(1, 2)
            ), size=3)
        )
        
        return Panel(
            pipeline_layout,
            title=f"Pipeline Analysis ({len(stages)} stages)",
            border_style=self.colors['secondary'],
            padding=(1, 2)
        )
    
    def _create_preview_panel(self, parsed_info: Dict) -> Panel:
        """Create a preview panel for command execution"""
        os_name = platform.system()
        
        preview_text = Text()
        preview_text.append("System: ", style="bold")
        preview_text.append(f"{os_name}\n\n", style=f"{self.colors['muted']}")
        
        if parsed_info['is_pipeline']:
            stages = parsed_info['stages']
            
            if not stages:
                preview_text.append("No valid pipeline stages to execute", style=self.colors['warning'])
            else:
                preview_text.append("Pipeline Execution Preview:\n", style="bold")
                
                for i, stage in enumerate(stages, 1):
                    action = stage.action
                    args = stage.args
                    
                    # Get native command
                    native_cmd = get_platform_command(action, args)
                    
                    preview_text.append(f"Stage {i}: ", style=f"bold {self.colors['muted']}")
                    
                    if isinstance(native_cmd, list):
                        preview_text.append(" ".join(native_cmd), style=self.colors['highlight'])
                    elif isinstance(native_cmd, str) and native_cmd.startswith("PYTHON"):
                        preview_text.append(f"Internal Python handler: {action}", style=self.colors['secondary'])
                    else:
                        preview_text.append(f"Unknown command: {action}", style=self.colors['error'])
                    
                    # Add pipe symbol if not the last stage
                    if i < len(stages):
                        preview_text.append(" | ", style=f"bold {self.colors['primary']}")
                    
                    preview_text.append("\n")
        else:
            command = parsed_info['command']
            action = command.get('action', 'unknown')
            args = command.get('args', [])
            
            if action in ['unrecognized', 'error', 'suggest']:
                if action == 'suggest' and not self.auto_suggest:
                    suggestion_id = command.get('suggestion_action_id')
                    preview_text.append("Suggestion: ", style="bold")
                    preview_text.append(f"Would execute '{suggestion_id}' if accepted\n", style=self.colors['highlight'])
                else:
                    preview_text.append("No executable command", style=self.colors['warning'])
            else:
                # Get native command
                native_cmd = get_platform_command(action, args)
                
                preview_text.append("Command: ", style="bold")
                
                if isinstance(native_cmd, list):
                    preview_text.append(" ".join(native_cmd), style=self.colors['highlight'])
                elif isinstance(native_cmd, str) and native_cmd.startswith("PYTHON"):
                    preview_text.append(f"Internal Python handler: {action}", style=self.colors['secondary'])
                    if "CHDIR" in native_cmd:
                        target = args[0] if args else "unknown"
                        preview_text.append(f"\nTarget directory: {target}", style=self.colors['muted'])
                    elif "MEM" in native_cmd:
                        preview_text.append("\nUsing psutil to get memory information", style=self.colors['muted'])
                else:
                    preview_text.append(f"Unknown command: {action}", style=self.colors['error'])
        
        # Warning for destructive commands
        destructive_actions = ['delete_file', 'delete_directory', 'rm', 'git_reset']
        if not parsed_info['is_pipeline']:
            action = parsed_info['command'].get('action', '')
            if action in destructive_actions:
                preview_text.append("\n\n⚠️ ", style=f"bold {self.colors['warning']}")
                preview_text.append("This is a destructive command!", style=f"bold {self.colors['warning']}")
        
        return Panel(
            preview_text,
            title="Command Preview",
            border_style=self.colors['secondary'],
            padding=(1, 2)
        )
    
    def _execute_command(self, parsed_info: Dict) -> Panel:
        """Execute the command and display results"""
        try:
            if parsed_info['is_pipeline']:
                stages = parsed_info['stages']
                
                if not stages:
                    return Panel(
                        "No valid pipeline stages to execute",
                        title="Execution Results",
                        border_style=self.colors['warning'],
                        padding=(1, 2)
                    )
                
                # Execute pipeline
                pipeline = CommandPipeline(self.parser, execute_command)
                result = pipeline.execute_pipeline(stages)
                
                return self._format_execution_results(result, is_pipeline=True)
            else:
                command = parsed_info['command']
                action = command.get('action', 'unknown')
                
                if action in ['unrecognized', 'error']:
                    return Panel(
                        f"Cannot execute command: {action}",
                        title="Execution Results",
                        border_style=self.colors['error'],
                        padding=(1, 2)
                    )
                
                if action == 'suggest':
                    if not self.auto_suggest:
                        # Ask for confirmation
                        suggestion_phrase = command.get('suggestion_phrase', 'that command')
                        suggestion_id = command.get('suggestion_action_id')
                        
                        if Confirm.ask(f"Execute suggested command '{suggestion_phrase}'?"):
                            # Extract args and create new command
                            args = command.get('args', [])
                            confirmed_command = {
                                'action': suggestion_id,
                                'args': args
                            }
                            
                            # Execute the confirmed command
                            result = self._mock_execution_result(confirmed_command)
                            return self._format_execution_results(result)
                        else:
                            return Panel(
                                "Suggestion rejected",
                                title="Execution Results",
                                border_style=self.colors['warning'],
                                padding=(1, 2)
                            )
                    else:
                        # Auto-suggest enabled, use the suggestion
                        suggestion_id = command.get('suggestion_action_id')
                        args = command.get('args', [])
                        confirmed_command = {
                            'action': suggestion_id,
                            'args': args
                        }
                        
                        result = self._mock_execution_result(confirmed_command)
                        return self._format_execution_results(result)
                
                # Execute the command
                result = self._mock_execution_result(command)
                return self._format_execution_results(result)
                
        except Exception as e:
            # Handle execution errors
            error_text = Text()
            error_text.append("Error executing command:\n", style=f"bold {self.colors['error']}")
            error_text.append(str(e), style=self.colors['error'])
            
            if self.debug:
                import traceback
                error_text.append("\n\nStacktrace:\n", style="bold")
                error_text.append(traceback.format_exc(), style=self.colors['muted'])
            
            return Panel(
                error_text,
                title="Execution Error",
                border_style=self.colors['error'],
                padding=(1, 2)
            )
    
    def _mock_execution_result(self, command: Dict) -> Dict:
        """
        For testing interface - returns a mock execution result
        In a real implementation, this would call execute_command
        """
        action = command.get('action', 'unknown')
        args = command.get('args', [])
        
        if self.test_mode:
            # Generate mock output for testing
            return {
                'success': True,
                'stdout': f"Mock output for action '{action}' with args {args}",
                'stderr': '',
                'returncode': 0
            }
        else:
            # Real execution
            try:
                # This would normally call execute_command directly
                # But for this testing interface, we'll wrap it to standardize the output
                execute_command(command)
                
                # Since execute_command doesn't return a structured result,
                # we'll provide a placeholder result
                return {
                    'success': True,
                    'stdout': f"Command '{action}' executed successfully with args {args}",
                    'stderr': '',
                    'returncode': 0
                }
            except Exception as e:
                return {
                    'success': False,
                    'stdout': '',
                    'stderr': str(e),
                    'returncode': 1
                }
    
    def _format_execution_results(self, result: Dict, is_pipeline: bool = False) -> Panel:
        """Format execution results for display"""
        success = result.get('success', False)
        stdout = result.get('stdout', '')
        stderr = result.get('stderr', '')
        return_code = result.get('returncode', 0)
        
        # Create content layout
        content_layout = Layout()
        
        # Status section
        status_text = Text()
        if success:
            status_text.append("✅ ", style=f"bold {self.colors['success']}")
            status_text.append("Command executed successfully", style=self.colors['success'])
            if is_pipeline:
                stages_executed = result.get('stages_executed', 0)
                status_text.append(f" ({stages_executed} stages)", style=self.colors['muted'])
        else:
            status_text.append("❌ ", style=f"bold {self.colors['error']}")
            status_text.append("Command execution failed", style=self.colors['error'])
            if is_pipeline:
                failed_stage = result.get('failed_stage', 'unknown')
                status_text.append(f" (failed at stage {failed_stage})", style=self.colors['muted'])
        
        status_text.append(f"\nReturn code: {return_code}", style=self.colors['muted'])
        
        status_panel = Panel(
            status_text,
            title="Execution Status",
            border_style=self.colors['success'] if success else self.colors['error'],
            padding=(1, 1)
        )
        
        # Output section
        output_text = ""
        if stdout:
            output_text = stdout
        
        # Try to detect if output is code/structured
        is_code = False
        if output_text and (
            output_text.startswith("{") or 
            output_text.startswith("[") or
            "def " in output_text or
            "class " in output_text or
            "import " in output_text
        ):
            is_code = True
        
        if output_text:
            if is_code:
                output_content = Syntax(output_text, "python", theme="monokai", line_numbers=True)
            else:
                output_content = output_text
        else:
            output_content = "No output"
        
        output_panel = Panel(
            output_content,
            title="Output",
            border_style=self.colors['secondary'],
            padding=(1, 1)
        )
        
        # Error section (if any)
        if stderr:
            error_panel = Panel(
                stderr,
                title="Errors",
                border_style=self.colors['error'],
                padding=(1, 1)
            )
            
            # Add error panel to layout
            content_layout.split(
                Layout(status_panel, size=4),
                Layout(output_panel),
                Layout(error_panel, size=8)
            )
        else:
            # Just status and output
            content_layout.split(
                Layout(status_panel, size=4),
                Layout(output_panel)
            )
        
        return Panel(
            content_layout,
            title="Execution Results",
            border_style=self.colors['primary'],
            padding=(1, 2)
        )
    
    def _collect_feedback(self, parsed_info: Dict) -> None:
        """Collect feedback about parsing accuracy"""
        self.console.print("\n[bold]Help Zyntax learn:[/bold]")
        was_correct = Confirm.ask("Did Zyntax understand your command correctly?", default=True)
        
        if was_correct:
            self.console.print(f"[{self.colors['success']}]✓ Thank you for your feedback![/]")
        else:
            # Get more detailed feedback
            correct_action = Prompt.ask(
                "What was the correct action?",
                default="skip"
            )
            
            if correct_action.lower() != "skip":
                # Record feedback using the parser's mechanism
                self.parser.record_feedback(
                    parsed_info['original'],
                    False,
                    correct_action
                )
                self.console.print(f"[{self.colors['success']}]✓ Feedback recorded. Zyntax will learn from this![/]")
    
    def display_help(self) -> None:
        """Display help information"""
        help_layout = Layout()
        
        # Create commands section
        commands_table = Table(show_header=True)
        commands_table.add_column("Command", style=f"bold {self.colors['secondary']}")
        commands_table.add_column("Description", style="white")
        
        commands = [
            ("Natural language", "Enter any natural language command to test Zyntax"),
            ("help", "Display this help screen"),
            ("exit, quit", "Exit the testing interface"),
            ("clear, cls", "Clear the screen"),
            ("settings", "Show all settings"),
            ("execution on/off", "Enable/disable command execution"),
            ("preview on/off", "Enable/disable command previews"),
            ("feedback on/off", "Enable/disable feedback collection"),
            ("suggest on/off", "Enable/disable auto-suggestion"),
            ("test mode on/off", "Enable/disable test mode (mocked execution)"),
        ]
        
        for cmd, desc in commands:
            commands_table.add_row(cmd, desc)
        
        # Create examples section
        examples_table = Table(show_header=True)
        examples_table.add_column("Example", style=f"bold {self.colors['highlight']}")
        examples_table.add_column("Description", style="white")
        
        examples = [
            ("list files", "Shows all files in the current directory"),
            ("create file test.py", "Creates a new file named test.py"),
            ("show memory usage", "Displays system memory information"),
            ("find all python files and count lines", "Pipeline: Lists Python files and counts them"),
            ("check git status", "Shows git repository status"),
            ("who am i", "Shows current user"),
        ]
        
        for example, desc in examples:
            examples_table.add_row(example, desc)
        
        # Create tips section
        tips_md = """
        ## Tips for effective testing
        
        • Start with simple commands before trying complex ones
        • Use the 'test mode on' setting to try commands without actually executing them
        • Provide feedback when Zyntax misunderstands to improve learning
        • Try variations of the same command to test robustness
        • Try pipeline commands like "find X and count Y"
        
        ## About NLP Testing
        
        This interface helps visualize how Zyntax processes natural language:
        
        1. **Parsing Phase**: Shows detected actions, arguments, and entities
        2. **Preview Phase**: Displays what commands would be executed
        3. **Execution Phase**: Shows the actual results of command execution
        4. **Feedback Phase**: Collects input to improve the system
        """
        
        tips_panel = Panel(
            Markdown(tips_md),
            title="Tips & Information",
            border_style=self.colors['primary'],
            padding=(1, 2)
        )
        
        # Create the layout
        help_layout.split(
            Layout(Panel(
                commands_table,
                title="Available Commands",
                border_style=self.colors['secondary'],
                padding=(1, 2)
            ), size=13),
            Layout(Panel(
                examples_table,
                title="Example Commands",
                border_style=self.colors['highlight'],
                padding=(1, 2)
            ), size=10),
            Layout(tips_panel)
        )
        
        # Update the main layout
        self.layout["visualization"].update(Panel(
            help_layout,
            title="Zyntax Testing Interface Help",
            border_style=self.colors['primary'],
            padding=(1, 2)
        ))
        
        self.layout["output"].update(Panel(
            Text(
                "Enter a command to start testing or 'exit' to quit",
                style=self.colors['secondary']
            ),
            title="Ready",
            border_style=self.colors['secondary'],
            padding=(1, 2)
        ))
        
        # Display the layout
        self.console.print(self.layout)
    
    def export_history(self, filename: str = None) -> None:
        """Export command history to a JSON file"""
        if not filename:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"zyntax_history_{timestamp}.json"
        
        # Prepare the history data (excluding complex objects)
        clean_history = []
        for entry in self.history:
            clean_entry = {
                'command': entry['command'],
                'timestamp': entry['timestamp'],
                'parsed': self._simplify_for_json(entry['parsed_info'])
            }
            clean_history.append(clean_entry)
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(clean_history, f, indent=2)
        
        self.console.print(f"[{self.colors['success']}]✓ History exported to {filename}[/]")
    
    def _simplify_for_json(self, obj):
        """Convert complex objects to JSON-serializable format"""
        if isinstance(obj, dict):
            return {k: self._simplify_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._simplify_for_json(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # For custom objects like PipelineStage
            return {k: self._simplify_for_json(v) for k, v in obj.__dict__.items()}
        else:
            # Try to convert to string if not JSON serializable
            try:
                json.dumps(obj)
                return obj
            except (TypeError, OverflowError):
                return str(obj)
    
    def run(self) -> None:
        """Run the testing interface main loop"""
        try:
            # Display welcome screen
            self.display_welcome()
            
            # Main loop
            running = True
            while running:
                try:
                    # Get user input
                    command = self.get_input()
                    
                    # Handle the command
                    running = self.handle_command(command)
                    
                except KeyboardInterrupt:
                    # Handle Ctrl+C
                    self.console.print("\n[bold]Operation cancelled.[/bold]")
                    if Confirm.ask("Exit Zyntax Tester?"):
                        running = False
                
                except Exception as e:
                    # Handle unexpected errors
                    self.console.print(f"[{self.colors['error']}]Error: {e}[/]")
                    if self.debug:
                        import traceback
                        self.console.print(Panel(
                            traceback.format_exc(),
                            title="Error Details",
                            border_style=self.colors['error']
                        ))
            
            # Export history if there's any
            if self.history and Confirm.ask("Export command history to file?"):
                self.export_history()
            
            # Goodbye message
            self.console.print(f"\n[{self.colors['primary']}]Thank you for using Zyntax Testing Interface![/]")
        
        except Exception as e:
            # Handle critical errors
            self.console.print(f"[{self.colors['error']}]Critical error: {e}[/]")
            if self.debug:
                import traceback
                self.console.print(Panel(
                    traceback.format_exc(),
                    title="Critical Error Details",
                    border_style=self.colors['error']
                ))
            return 1
        
        return 0


if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Zyntax Testing Interface")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--test", action="store_true", help="Enable test mode (no actual execution)")
    args = parser.parse_args()
    
    # Create and run the testing interface
    tester = ZyntaxTester(config_path=args.config, debug=args.debug)
    if args.test:
        tester.test_mode = True
    
    sys.exit(tester.run())