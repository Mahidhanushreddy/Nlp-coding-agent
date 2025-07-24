# Flask Backend for NLP Agent

This Flask backend handles the communication with the model API and provides a REST API for the TypeScript extension with enhanced file and folder analysis capabilities.

## Features

- **Advanced AST Analysis**: Comprehensive analysis of Python, JavaScript, TypeScript, HTML, CSS, JSON, YAML, and XML files
- **Main Program Extraction**: Automatically extracts the main program (entry point) from each uploaded file for better context understanding
- **Folder Structure Analysis**: Complete folder scanning with file type detection and statistics
- **Token Management**: Accurate token counting and intelligent context optimization
- **Multi-format Support**: Handles various file formats with specialized parsers
- **Complexity Metrics**: Provides code complexity analysis including nesting levels and function counts

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables (Optional):**
   Create a `.env` file in the flaskbackend directory to override default settings:
   ```
   MODEL_API_URL=https://api.groq.com/openai/v1/chat/completions
   API_KEY=Bearer your_api_key_here
   MODEL=llama3-8b-8192
   PORT=5000
   MAX_INPUT_TOKENS=6000
   MAX_TOKENS=4096
   ```

## Running the Backend

1. **Start the Flask server:**
   ```bash
   py app.py
   ```

2. **The server will start on:**
   - URL: `http://localhost:5000`
   - Health check: `http://localhost:5000/api/health`
   - Analyze endpoint: `http://localhost:5000/api/analyze-and-execute`

## API Endpoints

### Health Check
- **GET** `/api/health`
- Returns server status

### Analyze and Execute
- **POST** `/api/analyze-and-execute`
- **Body:** 
  ```json
  {
    "prompt": "your prompt here",
    "context": "optional context",
    "files": [
      {"path": "/path/to/file.py", "language": "python"},
      {"name": "script.js", "content": "base64_encoded_content", "type": "javascript"}
    ],
    "folders": [
      {"path": "/path/to/folder"}
    ]
  }
  ```
- **Response:** 
  ```json
  {
    "success": true,
    "type": "analysis",
    "output": "model response",
    "sections": {
      "analysis": "...",
      "packages": ["..."],
      "solution": "...",
      "run_commands": ["..."],
      "usage": "..."
    },
    "prompt": "original prompt",
    "context_tokens": 1234,
    "total_analyzed": 5,
    "analyzed_files": [
      {
        "name": "/path/to/file.py",
        "language": "python",
        "token_count": 1500,
        "lines": 45,
        "structure": "Imports: 3, Classes: 2, Functions: 5, Variables: 12",
        "error": null
      },
      {
        "name": "/path/to/folder",
        "type": "folder",
        "total_files": 10,
        "total_dirs": 3,
        "summary": "3 directories, 10 files, 5 python files, 3 javascript files, 2 json files",
        "error": null
      }
    ]
  }
  ```

## Configuration

The backend uses the following default configuration:
- Model API URL: `https://api.groq.com/openai/v1/chat/completions`
- Model: `llama3-8b-8192`
- Timeout: 30 seconds
- Max Retries: 3
- Max Input Tokens: 6000
- Max Response Tokens: 4096
- Max Context Length: 6000 characters

## Main Program Extraction

The backend automatically extracts the main program (entry point) from each uploaded file:

### Python Files
- Extracts code from `if __name__ == '__main__':` blocks
- Includes top-level statements and function calls
- Preserves the main execution logic

### JavaScript/TypeScript Files
- Identifies immediate function calls and console statements
- Extracts event listeners and initialization code
- Includes top-level assignments and function calls

### HTML Files
- Extracts `<body>` content and `<script>` tags
- Preserves the main UI structure and JavaScript logic
- Includes dynamic content and event handlers

### Configuration Files (JSON/YAML/XML)
- Extracts the main configuration content
- Preserves the structure and key-value pairs
- Limits to first 1000 characters for large files

## Token Management

The backend implements intelligent token management:
- **Accurate Token Counting**: Uses tiktoken for precise token calculation
- **Context Optimization**: Automatically optimizes context to fit within token limits
- **Priority-based Truncation**: Preserves important code structures when truncating
- **Binary Search Truncation**: Efficient text truncation to meet token limits

## File Analysis Capabilities

### Supported File Types
- **Python**: Full AST analysis with complexity metrics
- **JavaScript/TypeScript**: Enhanced regex-based analysis
- **HTML/CSS**: Tag and selector extraction
- **JSON**: Structure and key analysis
- **YAML**: Configuration file parsing
- **XML**: Tag structure analysis

### Analysis Features
- **Structure Summary**: Overview of code organization
- **Import Analysis**: External dependency tracking
- **Function/Class Detection**: Method and class identification
- **Main Program Extraction**: Extracts entry points and main execution logic from files
- **Complexity Metrics**: Nesting levels, function counts, variable counts
- **Token Counting**: Accurate token usage per file
- **Error Handling**: Graceful handling of parsing errors

## Error Handling

The backend includes comprehensive error handling for:
- Network connectivity issues
- API rate limiting
- Invalid requests
- Model API failures
- File parsing errors
- Token limit exceeded scenarios

## CORS

CORS is enabled to allow the TypeScript extension to communicate with the backend from different origins. 