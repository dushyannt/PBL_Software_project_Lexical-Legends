# Zyntax: A Smart NLP-Powered Terminal

Zyntax is an innovative command-line interface that leverages Natural Language Processing (NLP) to make terminal interactions more intuitive and user-friendly. It allows users to perform system operations using natural language commands instead of memorizing traditional terminal syntax.

## 🌟 Features

- **Natural Language Understanding**: Execute commands using everyday language
- **Cross-Platform Support**: Works on Windows, Linux, and macOS
- **Smart Command Suggestions**: Gets smarter with user interactions
- **File System Operations**: Create, delete, move, and manage files and directories
- **System Monitoring**: Check memory usage, disk space, and running processes
- **Git Integration**: Basic Git operations through natural language
- **Error Handling**: Intelligent error messages and suggestions

## 🏗️ System Architecture

### Core Components

1. **NLP Engine** (`nlp_engine/`)
   - Natural language processing and command parsing
   - Entity extraction and command matching
   - Fuzzy matching for command recognition
   - Uses spaCy for advanced NLP capabilities

2. **Command Executor** (`command_executor/`)
   - Platform-specific command mapping
   - Command execution and error handling
   - System operation implementation
   - Cross-platform compatibility layer

3. **Interface** (`interface/`)
   - User interaction handling
   - Command prompt and output formatting
   - Error message presentation
   - Rich text interface

4. **Testing** (`tests/`)
   - Unit tests for core components
   - Integration tests
   - Command validation tests

## 🔄 Workflow

1. **Command Input**
   - User enters natural language command
   - System captures and preprocesses input

2. **Command Processing**
   - NLP engine parses the input
   - Extracts command intent and entities
   - Matches with known command patterns

3. **Command Execution**
   - Command executor maps to system commands
   - Executes appropriate system operations
   - Handles platform-specific implementations

4. **Response Handling**
   - Processes command output
   - Formats and displays results
   - Handles errors and provides suggestions

## 🛠️ Implementation Details

### Dependencies

- **spaCy**: Natural language processing
- **rapidfuzz**: Fuzzy string matching
- **psutil**: System and process utilities
- **rich**: Enhanced terminal interface
- **colorama**: Cross-platform colored terminal text

### Command Types

1. **File Operations**
   - Create/delete files and directories
   - Move and copy files
   - List directory contents
   - Display file contents

2. **System Commands**
   - Memory usage monitoring
   - Disk space checking
   - Process listing
   - Directory navigation

3. **Git Operations**
   - Repository initialization
   - Status checking
   - Commit creation

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Zyntax-NLP-Terminal.git
   cd Zyntax-NLP-Terminal
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Unix/MacOS:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python main.py
   ```

## 💡 Usage Examples

```bash
# List files in current directory
Zyntax> Show me all files in this directory

# Create a new directory
Zyntax> Create a new directory called projects

# Check memory usage
Zyntax> Show me the memory usage

# Create a new file
Zyntax> Create a new file called test.txt

# Change directory
Zyntax> Change directory to downloads
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- spaCy team for the excellent NLP library
- All contributors and users of the project