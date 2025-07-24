from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
import re
import ast
import json
from typing import Dict, List, Any, Optional
import tempfile
import base64
import tiktoken  # For accurate token counting

# Load environment variables
load_dotenv()

def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens accurately using tiktoken"""
    try:
        encoding = tiktoken.get_encoding(model)
        return len(encoding.encode(text))
    except:
        # Fallback: rough estimation (4 chars = 1 token)
        return len(text) // 4

def estimate_tokens(text: str) -> int:
    """Estimate tokens when tiktoken is not available"""
    return len(text) // 4

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
DEFAULT_CONFIG = {
    'modelApiUrl': 'https://api.groq.com/openai/v1/chat/completions',
    'apiKey': '',
    'maxRetries': 3,
    'timeout': 30,
    'model': 'llama3-8b-8192',
    'maxContextLength': 6000,  # Increased for better analysis
    'maxTokens': 4096,  # Response token limit
    'maxInputTokens': 6000  # Input token limit (leaving room for response)
}

# --- SYSTEM PROMPT TEMPLATES ---
SYSTEM_PROMPTS = {
    "python_script": (
        "You are an expert Python coding assistant.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary packages, dependencies, and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., program_1.py) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\npip install <packages>\n```\n\n## 💻 Solution\n<file_name>\n```python\n<code>\n```\n\n## 🚀 Run Commands\n```bash\npython <file_name>\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "flask_app": (
        "You are an expert in building Python Flask web applications.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary packages, dependencies, and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., app.py) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\npip install flask <other_packages>\n```\n\n## 💻 Solution\n<file_name>\n```python\n<code>\n```\n\n## 🚀 Run Commands\n```bash\npython <file_name>\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "fastapi_app": (
        "You are an expert in building Python FastAPI web APIs.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary packages, dependencies, and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., main.py) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\npip install fastapi uvicorn <other_packages>\n```\n\n## 💻 Solution\n<file_name>\n```python\n<code>\n```\n\n## 🚀 Run Commands\n```bash\nuvicorn <file_name>:app --reload\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "react_app": (
        "You are an expert in building React web applications.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary packages, dependencies, and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., App.js) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\nnpx create-react-app <app_name>\ncd <app_name>\nnpm install <other_packages>\n```\n\n## 💻 Solution\n<file_name>\n```javascript\n<code>\n```\n\n## 🚀 Run Commands\n```bash\nnpm start\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "nodejs": (
        "You are an expert Node.js coding assistant.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary packages, dependencies, and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., app.js) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\nnpm install <packages>\n```\n\n## 💻 Solution\n<file_name>\n```javascript\n<code>\n```\n\n## 🚀 Run Commands\n```bash\nnode <file_name>\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "data_analysis": (
        "You are an expert data analysis assistant (Python, pandas, matplotlib, etc).\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary packages, dependencies, and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., analysis.py) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\npip install pandas matplotlib\n```\n\n## 💻 Solution\n<file_name>\n```python\n<code>\n```\n\n## 🚀 Run Commands\n```bash\npython <file_name>\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "minimal": (
        "You are an expert coding assistant.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary packages, dependencies, and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., script.py) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\n<commands>\n```\n\n## 💻 Solution\n<file_name>\n```<language>\n<code>\n```\n\n## 🚀 Run Commands\n```bash\n<commands>\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "default": (
        "You are an expert AI coding assistant that analyzes, thinks, and executes based on user prompts.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary packages, dependencies, and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., program_1.py) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\n<commands>\n```\n\n## 💻 Solution\n<file_name>\n```<language>\n<code>\n```\n\n## 🚀 Run Commands\n```bash\n<commands>\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "webapp": (
        "You are an expert in building modern web applications using HTML, CSS, and JavaScript.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary files and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., index.html) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\n<commands>\n```\n\n## 💻 Solution\n<file_name>\n```<language>\n<code>\n```\n\n## 🚀 Run Commands\n```bash\n<commands>\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "springboot": (
        "You are an expert in building Java Spring Boot applications.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary dependencies and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., Application.java, pom.xml) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\n<commands>\n```\n\n## 💻 Solution\n<file_name>\n```java\n<code>\n```\n\n## 🚀 Run Commands\n```bash\n<commands>\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "c": (
        "You are an expert in C programming.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary files and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., main.c) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\ngcc <file_name> -o <output>\n```\n\n## 💻 Solution\n<file_name>\n```c\n<code>\n```\n\n## 🚀 Run Commands\n```bash\n./<output>\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "java": (
        "You are an expert in Java programming.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary files and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., Main.java) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\njavac <file_name>\n```\n\n## 💻 Solution\n<file_name>\n```java\n<code>\n```\n\n## 🚀 Run Commands\n```bash\njava <MainClass>\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "angular_app": (
        "You are an expert in building Angular web applications.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary packages, dependencies, and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., app.component.ts) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\nnpm install -g @angular/cli\nng new <app_name>\ncd <app_name>\nnpm install <other_packages>\n```\n\n## 💻 Solution\n<file_name>\n```typescript\n<code>\n```\n\n## 🚀 Run Commands\n```bash\nng serve\n```\n\n## 📝 Usage Instructions\n<usage>"
    ),
    "nlp_app": (
        "You are an expert in building Natural Language Processing (NLP) applications.\n"
        "Always include all required installation commands, complete runnable code, and any additional information needed to run and use the solution, based on the keys/sections in the response format.\n"
        "ANALYSIS & EXECUTION GUIDELINES:\n"
        "1. Analyze: Understand the user's intent and requirements\n"
        "2. Think: Plan the solution with necessary NLP libraries, models, and steps\n"
        "3. Execute: Provide complete, runnable solutions with installation commands\n"
        "IMPORTANT: For each code block in the Solution section, always include a single-line header with the file name (e.g., nlp_app.py) immediately before the code block. The file name in the header must match the file name used in the Run Commands section.\n"
        "RESPONSE FORMAT:\n"
        "## 📋 Analysis\n<analysis>\n\n## 🛠️ Required Packages\n```bash\npip install <nlp_packages>\n```\n\n## 💻 Solution\n<file_name>\n```python\n<code>\n```\n\n## 🚀 Run Commands\n```bash\npython <file_name>\n```\n\n## 📝 Usage Instructions\n<usage>"
    )
}

def select_system_prompt(user_prompt: str, context: str) -> str:
    prompt = user_prompt.lower()
    ctx = context.lower() if context else ""
    # NLP app
    if "nlp" in prompt or "natural language processing" in prompt or "text analysis" in prompt:
        return "nlp_app"
    # Angular app
    if ("angular" in prompt or "typescript" in prompt) and not ("react" in prompt or "fastapi" in prompt):
        return "angular_app"
    # Java programming
    if any(word in prompt for word in ["java", "javac", "maven", "gradle"]) or any(word in ctx for word in ["java", ".java"]):
        return "java"
    # C programming
    if any(word in prompt for word in ["c programming", "gcc", "c code"]) or any(word in ctx for word in ["c", ".c"]):
        return "c"
    # Flask app
    if any(word in prompt for word in ["flask"]) or "flask" in ctx:
        return "flask_app"
    # FastAPI app
    if any(word in prompt for word in ["fastapi"]) or "fastapi" in ctx:
        return "fastapi_app"
    # React app
    if any(word in prompt for word in ["react", "jsx", "tsx"]) or "react" in ctx:
        return "react_app"
    # Data analysis
    if any(word in prompt for word in ["analyze", "plot", "dataframe", "pandas", "matplotlib"]) or "pandas" in ctx:
        return "data_analysis"
    # Web app (generic)
    if any(word in ctx for word in ["html", "css", "javascript"]) or "web app" in prompt:
        return "webapp"
    # Node.js
    if "node.js" in prompt or "nodejs" in prompt or "node" in ctx:
        return "nodejs"
    # Python script
    if "python" in ctx or "py" in ctx or "python" in prompt:
        return "python_script"
    # Minimal (if user says minimal, script only, or similar)
    if any(word in prompt for word in ["minimal", "script only", "just code", "no explanation"]):
        return "minimal"
    # Default
    return "default"

class ASTContextAnalyzer:
    """Analyzes code using AST to extract relevant context with maximum accuracy"""
    
    def __init__(self):
        self.important_nodes = {
            'FunctionDef', 'ClassDef', 'Import', 'ImportFrom', 
            'Assign', 'Expr', 'Return', 'If', 'For', 'While',
            'Try', 'With', 'AsyncFunctionDef', 'AsyncFor', 'AsyncWith',
            'Call', 'Attribute', 'Name', 'Constant', 'List', 'Dict', 'Tuple'
        }
    
    def analyze_file(self, file_path: str, language: str) -> Dict[str, Any]:
        """Analyze a file and extract relevant context based on language with maximum accuracy"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if language == 'python':
                return self._analyze_python_file(content, file_path)
            elif language in ['javascript', 'typescript']:
                return self._analyze_js_file(content, file_path)
            elif language in ['html', 'css']:
                return self._analyze_markup_file(content, file_path)
            elif language == 'json':
                return self._analyze_json_file(content, file_path)
            elif language == 'yaml' or file_path.endswith(('.yml', '.yaml')):
                return self._analyze_yaml_file(content, file_path)
            elif language == 'xml':
                return self._analyze_xml_file(content, file_path)
            elif language == 'java':
                return self._analyze_java_file(content, file_path)
            elif language == 'c':
                return self._analyze_c_file(content, file_path)
            else:
                return self._analyze_generic_file(content, file_path)
        except Exception as e:
            return {
                'file_path': file_path,
                'language': language,
                'error': str(e),
                'content': content[:500] if 'content' in locals() else '',
                'token_count': count_tokens(content[:500]) if 'content' in locals() else 0
            }
    
    def analyze_folder_structure(self, folder_path: str) -> Dict[str, Any]:
        """Analyze folder structure and extract relevant information"""
        try:
            structure = {
                'folder_path': folder_path,
                'files': [],
                'directories': [],
                'file_types': {},
                'total_files': 0,
                'total_dirs': 0,
                'summary': ''
            }
            
            for root, dirs, files in os.walk(folder_path):
                rel_root = os.path.relpath(root, folder_path)
                if rel_root == '.':
                    rel_root = ''
                
                # Add directories
                for dir_name in dirs:
                    if not dir_name.startswith('.'):  # Skip hidden dirs
                        structure['directories'].append(os.path.join(rel_root, dir_name))
                        structure['total_dirs'] += 1
                
                # Add files
                for file_name in files:
                    if not file_name.startswith('.'):  # Skip hidden files
                        file_path = os.path.join(rel_root, file_name)
                        full_path = os.path.join(root, file_name)
                        ext = os.path.splitext(file_name)[1].lower()
                        
                        # Determine language from extension
                        language_map = {
                            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                            '.html': 'html', '.css': 'css', '.json': 'json',
                            '.yml': 'yaml', '.yaml': 'yaml', '.xml': 'xml',
                            '.md': 'markdown', '.txt': 'text', '.java': 'java', '.c': 'c'
                        }
                        language = language_map.get(ext, 'unknown')
                        
                        # Count file types
                        if language not in structure['file_types']:
                            structure['file_types'][language] = 0
                        structure['file_types'][language] += 1
                        
                        # Get file size
                        try:
                            size = os.path.getsize(full_path)
                            structure['files'].append({
                                'path': file_path,
                                'language': language,
                                'size': size,
                                'size_kb': size / 1024
                            })
                            structure['total_files'] += 1
                        except:
                            pass
            
            # Create summary
            summary_parts = []
            if structure['total_dirs'] > 0:
                summary_parts.append(f"{structure['total_dirs']} directories")
            if structure['total_files'] > 0:
                summary_parts.append(f"{structure['total_files']} files")
            
            for lang, count in structure['file_types'].items():
                if count > 0:
                    summary_parts.append(f"{count} {lang} files")
            
            structure['summary'] = ', '.join(summary_parts)
            return structure
            
        except Exception as e:
            return {
                'folder_path': folder_path,
                'error': str(e),
                'files': [],
                'directories': [],
                'total_files': 0,
                'total_dirs': 0
            }
    
    def _analyze_python_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze Python file using AST with maximum accuracy"""
        try:
            tree = ast.parse(content)
            analyzer = PythonASTAnalyzer()
            analyzer.visit(tree)
            
            # Extract main program
            main_program = analyzer.extract_main_program(content)
            
            # Calculate token count
            token_count = count_tokens(content)
            
            return {
                'file_path': file_path,
                'language': 'python',
                'imports': analyzer.imports,
                'classes': analyzer.classes,
                'functions': analyzer.functions,
                'variables': analyzer.variables,
                'structure': analyzer.get_structure_summary(),
                'main_program': main_program,
                'content': content,
                'token_count': token_count,
                'lines': len(content.split('\n')),
                'complexity': analyzer.get_complexity_metrics()
            }
        except SyntaxError as e:
            return {
                'file_path': file_path,
                'language': 'python',
                'error': f'Syntax error: {str(e)}',
                'content': content[:500],
                'token_count': count_tokens(content[:500])
            }
    
    def _analyze_js_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript file with enhanced accuracy"""
        # Enhanced regex-based analysis for JS/TS
        imports = re.findall(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content)
        functions = re.findall(r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*\(|let\s+(\w+)\s*=\s*\(|var\s+(\w+)\s*=\s*\()', content)
        classes = re.findall(r'class\s+(\w+)', content)
        variables = re.findall(r'(?:const|let|var)\s+(\w+)', content)
        
        # Extract more patterns
        arrow_functions = re.findall(r'(\w+)\s*=\s*\([^)]*\)\s*=>', content)
        async_functions = re.findall(r'async\s+(?:function\s+)?(\w+)', content)
        
        # Extract main program (entry point)
        main_program = self._extract_js_main_program(content)
        
        token_count = count_tokens(content)
        
        return {
            'file_path': file_path,
            'language': 'javascript',
            'imports': imports,
            'functions': [f[0] or f[1] or f[2] or f[3] for f in functions if any(f)],
            'arrow_functions': arrow_functions,
            'async_functions': async_functions,
            'classes': classes,
            'variables': variables,
            'main_program': main_program,
            'content': content,
            'token_count': token_count,
            'lines': len(content.split('\n'))
        }
    
    def _analyze_markup_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze HTML/CSS file"""
        if file_path.endswith('.html'):
            tags = re.findall(r'<(\w+)', content)
            # Extract main program (body content and scripts)
            main_program = self._extract_html_main_program(content)
            return {
                'file_path': file_path,
                'language': 'html',
                'tags': list(set(tags)),
                'main_program': main_program,
                'content': content
            }
        else:
            selectors = re.findall(r'([.#]?\w+)\s*{', content)
            return {
                'file_path': file_path,
                'language': 'css',
                'selectors': list(set(selectors)),
                'content': content
            }
    
    def _analyze_generic_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze generic file"""
        # Extract main program (first part of the file)
        main_program = content[:1000] if len(content) > 1000 else content
        
        return {
            'file_path': file_path,
            'language': 'unknown',
            'main_program': main_program,
            'content': content[:1000]  # Limit content for unknown files
        }
    
    def optimize_context(self, context: str, max_length: int = 4000) -> str:
        """Optimize context by extracting the most relevant parts"""
        if len(context) <= max_length:
            return context
        
        # Split context into sections
        sections = context.split('\n\n')
        optimized_sections = []
        current_length = 0
        
        for section in sections:
            if current_length + len(section) + 2 <= max_length:
                optimized_sections.append(section)
                current_length += len(section) + 2
            else:
                # Try to extract key parts from this section
                key_parts = self._extract_key_parts(section)
                if current_length + len(key_parts) + 2 <= max_length:
                    optimized_sections.append(key_parts)
                    current_length += len(key_parts) + 2
                else:
                    break
        
        return '\n\n'.join(optimized_sections)
    
    def _extract_key_parts(self, section: str) -> str:
        """Extract key parts from a section"""
        lines = section.split('\n')
        key_lines = []
        
        for line in lines:
            # Keep lines with important keywords
            important_keywords = ['def ', 'class ', 'import ', 'from ', 'function ', 'const ', 'let ', 'var ']
            if any(keyword in line for keyword in important_keywords):
                key_lines.append(line)
            elif line.strip().startswith('#') or line.strip().startswith('//'):
                key_lines.append(line)
        
        return '\n'.join(key_lines[:10])  # Limit to 10 key lines

    def _analyze_json_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze JSON file"""
        try:
            data = json.loads(content)
            token_count = count_tokens(content)
            
            # Extract main program (the JSON content itself)
            main_program = content[:1000] if len(content) > 1000 else content
            
            return {
                'file_path': file_path,
                'language': 'json',
                'keys': list(data.keys()) if isinstance(data, dict) else [],
                'type': type(data).__name__,
                'main_program': main_program,
                'content': content,
                'token_count': token_count,
                'lines': len(content.split('\n'))
            }
        except json.JSONDecodeError as e:
            return {
                'file_path': file_path,
                'language': 'json',
                'error': f'JSON decode error: {str(e)}',
                'content': content[:500],
                'token_count': count_tokens(content[:500])
            }
    
    def _analyze_yaml_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze YAML file"""
        try:
            import yaml
            data = yaml.safe_load(content)
            token_count = count_tokens(content)
            
            # Extract main program (the YAML content itself)
            main_program = content[:1000] if len(content) > 1000 else content
            
            return {
                'file_path': file_path,
                'language': 'yaml',
                'keys': list(data.keys()) if isinstance(data, dict) else [],
                'type': type(data).__name__,
                'main_program': main_program,
                'content': content,
                'token_count': token_count,
                'lines': len(content.split('\n'))
            }
        except Exception as e:
            return {
                'file_path': file_path,
                'language': 'yaml',
                'error': f'YAML parse error: {str(e)}',
                'content': content[:500],
                'token_count': count_tokens(content[:500])
            }
    
    def _extract_js_main_program(self, content: str) -> str:
        """Extract the main program (entry point) from JavaScript/TypeScript code"""
        try:
            lines = content.split('\n')
            main_lines = []
            
            # Look for common entry point patterns
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # Check for immediate function calls
                if (stripped.startswith('console.log(') or 
                    stripped.startswith('document.') or
                    stripped.startswith('window.') or
                    stripped.startswith('process.') or
                    stripped.startswith('require(') or
                    stripped.startswith('import(') or
                    re.match(r'^\w+\(', stripped) or
                    re.match(r'^\w+\.\w+\(', stripped)):
                    main_lines.append(line)
                
                # Check for top-level assignments that might be initialization
                elif re.match(r'^(const|let|var)\s+\w+\s*=', stripped):
                    main_lines.append(line)
                
                # Check for event listeners or initialization code
                elif ('addEventListener' in stripped or 
                      'DOMContentLoaded' in stripped or
                      'window.onload' in stripped):
                    main_lines.append(line)
            
            # If no main program found, return first few non-empty lines
            if not main_lines:
                non_empty_lines = [line for line in lines if line.strip()]
                main_lines = non_empty_lines[:10]  # First 10 non-empty lines
            
            return '\n'.join(main_lines)
        except Exception as e:
            return f"// Error extracting main program: {str(e)}"
    
    def _extract_html_main_program(self, content: str) -> str:
        """Extract the main program (entry point) from HTML code"""
        try:
            # Extract body content and scripts
            body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
            script_matches = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE)
            
            main_parts = []
            
            # Add body content
            if body_match:
                body_content = body_match.group(1).strip()
                if body_content:
                    main_parts.append(f"<!-- Body Content -->\n{body_content}")
            
            # Add script content
            if script_matches:
                for i, script in enumerate(script_matches):
                    script_content = script.strip()
                    if script_content:
                        main_parts.append(f"<!-- Script {i+1} -->\n{script_content}")
            
            # If no body or scripts found, return the whole content
            if not main_parts:
                return content[:1000]  # First 1000 chars
            
            return '\n\n'.join(main_parts)
        except Exception as e:
            return f"<!-- Error extracting main program: {str(e)} -->"
    
    def _extract_java_main_program(self, content: str) -> str:
        """Extract the main program (entry point) from Java code"""
        try:
            # Look for main method
            main_match = re.search(r'public\s+static\s+void\s+main\s*\([^)]*\)\s*\{[^}]*\}', content, re.DOTALL)
            if main_match:
                return main_match.group(0)
            
            # Look for any public static methods that might be entry points
            static_methods = re.findall(r'public\s+static\s+\w+\s+\w+\s*\([^)]*\)\s*\{[^}]*\}', content, re.DOTALL)
            if static_methods:
                return static_methods[0]
            
            # If no main method found, return first few non-empty lines
            lines = content.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            return '\n'.join(non_empty_lines[:10])  # First 10 non-empty lines
        except Exception as e:
            return f"// Error extracting main program: {str(e)}"
    
    def _extract_c_main_program(self, content: str) -> str:
        """Extract the main program (entry point) from C code"""
        try:
            # Look for main function
            main_match = re.search(r'int\s+main\s*\([^)]*\)\s*\{[^}]*\}', content, re.DOTALL)
            if main_match:
                return main_match.group(0)
            
            # Look for any function that might be an entry point
            functions = re.findall(r'\w+\s+\w+\s*\([^)]*\)\s*\{[^}]*\}', content, re.DOTALL)
            if functions:
                return functions[0]
            
            # If no main function found, return first few non-empty lines
            lines = content.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            return '\n'.join(non_empty_lines[:10])  # First 10 non-empty lines
        except Exception as e:
            return f"// Error extracting main program: {str(e)}"
    
    def _analyze_xml_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze XML file"""
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)
            token_count = count_tokens(content)
            
            # Extract tags
            tags = set()
            for elem in root.iter():
                tags.add(elem.tag)
            
            # Extract main program (the XML content itself)
            main_program = content[:1000] if len(content) > 1000 else content
            
            return {
                'file_path': file_path,
                'language': 'xml',
                'root_tag': root.tag,
                'tags': list(tags),
                'main_program': main_program,
                'content': content,
                'token_count': token_count,
                'lines': len(content.split('\n'))
            }
        except Exception as e:
            return {
                'file_path': file_path,
                'language': 'xml',
                'error': f'XML parse error: {str(e)}',
                'content': content[:500],
                'token_count': count_tokens(content[:500])
            }
    
    def _analyze_java_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze Java file with enhanced accuracy"""
        # Enhanced regex-based analysis for Java
        imports = re.findall(r'import\s+([^;]+);', content)
        classes = re.findall(r'(?:public\s+)?class\s+(\w+)', content)
        methods = re.findall(r'(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:<[^>]+>\s+)?(\w+)\s+(\w+)\s*\([^)]*\)\s*\{', content)
        variables = re.findall(r'(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(\w+)\s+(\w+)\s*[=;]', content)
        
        # Extract main method
        main_method = re.search(r'public\s+static\s+void\s+main\s*\([^)]*\)\s*\{[^}]*\}', content, re.DOTALL)
        main_program = main_method.group(0) if main_method else ""
        
        # Extract main program (entry point)
        if not main_program:
            main_program = self._extract_java_main_program(content)
        
        token_count = count_tokens(content)
        
        return {
            'file_path': file_path,
            'language': 'java',
            'imports': imports,
            'classes': classes,
            'methods': [f"{method[1]}()" for method in methods if method[1] != 'main'],
            'variables': [f"{var[1]}" for var in variables],
            'main_program': main_program,
            'content': content,
            'token_count': token_count,
            'lines': len(content.split('\n'))
        }
    
    def _analyze_c_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze C file with enhanced accuracy"""
        # Enhanced regex-based analysis for C
        includes = re.findall(r'#include\s*[<"]([^>"]+)[>"]', content)
        functions = re.findall(r'(\w+)\s+(\w+)\s*\([^)]*\)\s*\{', content)
        variables = re.findall(r'(?:int|char|float|double|long|short|unsigned)\s+(\w+)\s*[=;]', content)
        defines = re.findall(r'#define\s+(\w+)', content)
        
        # Extract main function
        main_function = re.search(r'int\s+main\s*\([^)]*\)\s*\{[^}]*\}', content, re.DOTALL)
        main_program = main_function.group(0) if main_function else ""
        
        # Extract main program (entry point)
        if not main_program:
            main_program = self._extract_c_main_program(content)
        
        token_count = count_tokens(content)
        
        return {
            'file_path': file_path,
            'language': 'c',
            'includes': includes,
            'functions': [f"{func[1]}()" for func in functions if func[1] != 'main'],
            'variables': variables,
            'defines': defines,
            'main_program': main_program,
            'content': content,
            'token_count': token_count,
            'lines': len(content.split('\n'))
        }

class PythonASTAnalyzer(ast.NodeVisitor):
    """AST visitor for Python code analysis with enhanced accuracy"""
    
    def __init__(self):
        self.imports = []
        self.classes = []
        self.functions = []
        self.variables = []
        self.current_class = None
        self.main_program = ""
        self.complexity_metrics = {
            'total_lines': 0,
            'function_count': 0,
            'class_count': 0,
            'import_count': 0,
            'variable_count': 0,
            'nested_levels': 0,
            'max_nesting': 0
        }
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(f"import {alias.name}")
        self.complexity_metrics['import_count'] += len(node.names)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        module = node.module or ''
        names = ', '.join(alias.name for alias in node.names)
        self.imports.append(f"from {module} import {names}")
        self.complexity_metrics['import_count'] += len(node.names)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        class_info = {
            'name': node.name,
            'bases': [base.id for base in node.bases if hasattr(base, 'id')],
            'methods': [],
            'decorators': [d.id for d in node.decorator_list if hasattr(d, 'id')]
        }
        self.current_class = class_info
        self.classes.append(class_info)
        self.complexity_metrics['class_count'] += 1
        self.generic_visit(node)
        self.current_class = None
    
    def visit_FunctionDef(self, node):
        func_info = {
            'name': node.name,
            'args': [arg.arg for arg in node.args.args],
            'class': self.current_class['name'] if self.current_class else None,
            'decorators': [d.id for d in node.decorator_list if hasattr(d, 'id')],
            'is_async': isinstance(node, ast.AsyncFunctionDef)
        }
        self.functions.append(func_info)
        self.complexity_metrics['function_count'] += 1
        self.generic_visit(node)
    
    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.variables.append(target.id)
                self.complexity_metrics['variable_count'] += 1
        self.generic_visit(node)
    
    def visit_If(self, node):
        self.complexity_metrics['nested_levels'] += 1
        self.complexity_metrics['max_nesting'] = max(
            self.complexity_metrics['max_nesting'], 
            self.complexity_metrics['nested_levels']
        )
        self.generic_visit(node)
        self.complexity_metrics['nested_levels'] -= 1
    
    def visit_For(self, node):
        self.complexity_metrics['nested_levels'] += 1
        self.complexity_metrics['max_nesting'] = max(
            self.complexity_metrics['max_nesting'], 
            self.complexity_metrics['nested_levels']
        )
        self.generic_visit(node)
        self.complexity_metrics['nested_levels'] -= 1
    
    def visit_While(self, node):
        self.complexity_metrics['nested_levels'] += 1
        self.complexity_metrics['max_nesting'] = max(
            self.complexity_metrics['max_nesting'], 
            self.complexity_metrics['nested_levels']
        )
        self.generic_visit(node)
        self.complexity_metrics['nested_levels'] -= 1
    
    def extract_main_program(self, content: str) -> str:
        """Extract the main program (entry point) from Python code"""
        try:
            tree = ast.parse(content)
            main_lines = []
            
            for node in tree.body:
                # Check if this is a main execution block (not in function/class)
                if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
                    # Check for `if __name__ == '__main__':` pattern
                    if (isinstance(node.test.left, ast.Name) and 
                        node.test.left.id == '__name__' and
                        isinstance(node.test.ops[0], ast.Eq) and
                        isinstance(node.test.comparators[0], ast.Constant) and
                        node.test.comparators[0].value == '__main__'):
                        # Extract the main block
                        for stmt in node.body:
                            main_lines.append(ast.unparse(stmt))
                        break
                elif isinstance(node, (ast.Expr, ast.Assign, ast.Call)):
                    # Top-level statements that are not in functions/classes
                    main_lines.append(ast.unparse(node))
            
            return '\n'.join(main_lines)
        except Exception as e:
            return f"# Error extracting main program: {str(e)}"
    
    def get_structure_summary(self) -> str:
        """Get a comprehensive summary of the code structure"""
        summary = []
        if self.imports:
            summary.append(f"Imports: {len(self.imports)}")
        if self.classes:
            summary.append(f"Classes: {len(self.classes)}")
        if self.functions:
            summary.append(f"Functions: {len(self.functions)}")
        if self.variables:
            summary.append(f"Variables: {len(self.variables)}")
        if self.complexity_metrics['max_nesting'] > 0:
            summary.append(f"Max nesting: {self.complexity_metrics['max_nesting']}")
        return ', '.join(summary)
    
    def get_complexity_metrics(self) -> Dict[str, Any]:
        """Get detailed complexity metrics"""
        return self.complexity_metrics.copy()

class ModelAPIClient:
    def __init__(self, config):
        self.config = config
        self.context_analyzer = ASTContextAnalyzer()
    
    def generate_full_response(self, prompt: str, context: str = "") -> str:
        try:
            # Calculate token counts
            prompt_tokens = count_tokens(prompt)
            context_tokens = count_tokens(context) if context else 0
            # --- Use dynamic system prompt selection ---
            system_prompt_key = select_system_prompt(prompt, context)
            system_prompt = SYSTEM_PROMPTS[system_prompt_key]
            system_prompt_tokens = count_tokens(system_prompt)
            total_input_tokens = prompt_tokens + context_tokens + system_prompt_tokens
            # Check if we exceed input token limit
            if total_input_tokens > self.config['maxInputTokens']:
                # Optimize context to fit within token limit
                available_tokens = self.config['maxInputTokens'] - prompt_tokens - system_prompt_tokens
                if available_tokens > 0:
                    context = self._optimize_context_by_tokens(context, available_tokens)
                else:
                    # If even without context we're over limit, truncate prompt
                    context = ""
                    prompt = self._truncate_text_by_tokens(prompt, self.config['maxInputTokens'] - system_prompt_tokens)
            # --- Use selected system prompt ---
            print(prompt)
            print(system_prompt)
            messages = [
                {'role': 'system', 'content': system_prompt}
            ]
            if context:
                messages.append({
                    'role': 'user', 
                    'content': f"Context:\n{context}\n\nUser Request: {prompt}"
                })
            else:
                messages.append({'role': 'user', 'content': prompt})
            print(context)
            response = requests.post(
                self.config['modelApiUrl'],
                json={
                    'model': self.config.get('model', 'llama3-8b-8192'),
                    'messages': messages,
                    'max_tokens': self.config.get('maxTokens', 4096),
                    'temperature': 0.7,
                    'top_p': 0.9
                },
                headers={
                    'Authorization': self.config['apiKey'],
                    'Content-Type': 'application/json'
                },
                timeout=self.config['timeout']
            )
            if response.status_code == 200:
                data = response.json()
                if data and 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content']
                else:
                    raise Exception('No response from model API')
            else:
                raise Exception(f'API request failed with status {response.status_code}: {response.text}')
        except Exception as error:
            print(f'Error calling model API: {error}')
            return f'Error: Unable to get a response from the model. {str(error)}'
    
    def _get_system_prompt(self) -> str:
        """Get the enhanced system prompt"""
        return """You are an expert AI coding assistant that analyzes, thinks, and executes based on user prompts.

ANALYSIS & EXECUTION GUIDELINES:
1. **Analyze**: Understand the user's intent and requirements
2. **Think**: Plan the solution with necessary packages, dependencies, and steps
3. **Execute**: Provide complete, runnable solutions with installation commands

RESPONSE FORMAT:
Always structure your response with these sections:

## 📋 Analysis
Brief analysis of the user's request

## 🛠️ Required Packages
List of necessary packages with installation commands:
```bash
pip install package1 package2
npm install package1 package2
# etc.
```

## 💻 Solution
Complete code with proper syntax highlighting:
```language
// Your complete code here
```

## 🚀 Run Commands
Commands to execute the solution:
```bash
python script.py
node app.js
# etc.
```

## 📝 Usage Instructions
Brief instructions on how to use the solution

EXAMPLES:
- For web apps: Include HTML, CSS, JS with run commands
- For Python scripts: Include imports, main code, and execution commands
- For Node.js: Include package.json, dependencies, and run commands
- For data analysis: Include pandas, matplotlib, and visualization commands

Always provide complete, copy-paste ready solutions with all necessary setup steps."""
    
    def _optimize_context_by_tokens(self, context: str, max_tokens: int) -> str:
        """Optimize context to fit within token limit"""
        if count_tokens(context) <= max_tokens:
            return context
        
        # Split into sections and prioritize
        sections = context.split('\n\n')
        optimized_sections = []
        current_tokens = 0
        
        for section in sections:
            section_tokens = count_tokens(section)
            if current_tokens + section_tokens + 2 <= max_tokens:
                optimized_sections.append(section)
                current_tokens += section_tokens + 2
            else:
                # Try to extract key parts from this section
                key_parts = self._extract_key_parts_by_tokens(section, max_tokens - current_tokens)
                if key_parts:
                    optimized_sections.append(key_parts)
                    break
        
        return '\n\n'.join(optimized_sections)
    
    def _extract_key_parts_by_tokens(self, section: str, available_tokens: int) -> str:
        """Extract key parts from a section within token limit"""
        lines = section.split('\n')
        key_lines = []
        current_tokens = 0
        
        for line in lines:
            # Keep lines with important keywords
            important_keywords = ['def ', 'class ', 'import ', 'from ', 'function ', 'const ', 'let ', 'var ']
            if any(keyword in line for keyword in important_keywords):
                line_tokens = count_tokens(line)
                if current_tokens + line_tokens + 1 <= available_tokens:
                    key_lines.append(line)
                    current_tokens += line_tokens + 1
                else:
                    break
            elif line.strip().startswith('#') or line.strip().startswith('//'):
                line_tokens = count_tokens(line)
                if current_tokens + line_tokens + 1 <= available_tokens:
                    key_lines.append(line)
                    current_tokens += line_tokens + 1
                else:
                    break
        
        return '\n'.join(key_lines)
    
    def _truncate_text_by_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit"""
        if count_tokens(text) <= max_tokens:
            return text
        
        # Binary search to find the right truncation point
        left, right = 0, len(text)
        while left < right:
            mid = (left + right) // 2
            if count_tokens(text[:mid]) <= max_tokens:
                left = mid + 1
            else:
                right = mid
        
        return text[:left]

    def parse_response_sections(self, response_text):
        """
        Parse the response into structured sections for better UI handling,
        supporting multiple sections with the same header.
        """
        # Define the section headers in order
        section_headers = [
            "Analysis",
            "Required Packages",
            "Solution",
            "Run Commands",
            "Usage Instructions"
        ]
        # Regex to match all section headers and their content
        section_pattern = re.compile(
            r'^(?:\*\*\s*)?##\s*(?:[^\w]*)?(' + '|'.join(re.escape(h) for h in section_headers) + r')\s*(?:\*\*)?\s*\n(.*?)(?=^(?:\*\*\s*)?## |\Z)',
            re.DOTALL | re.MULTILINE | re.IGNORECASE
        )
        # Find all sections
        sections_found = list(section_pattern.finditer(response_text))
        # Group by header
        sections = {header: [] for header in section_headers}
        for match in sections_found:
            header = match.group(1).strip()
            content = match.group(2).strip()
            if header in sections:
                sections[header].append(content)
        # For single-section fields, flatten to string
        for header in ["Analysis", "Usage Instructions"]:
            if sections[header]:
                sections[header] = sections[header][0]
            else:
                sections[header] = ""
        # For multi-section fields, keep as lists
        # Parse code blocks in Solution sections
        files = []
        solution_blocks = []
        for solution in sections["Solution"]:
            # Find all code blocks with filename headers
            code_block_pattern = re.compile(
                r'^(?:\*\*\s*)?(?:`\s*)*([\w_.\-/]+)(?:\s*`)*(?:\s*\*\*)?\s*\n```([\w+-]*)\n(.*?)\n```',
                re.DOTALL | re.MULTILINE
            )
            last_end = 0
            for match in code_block_pattern.finditer(solution):
                # Add any text before the code block (e.g., explanations)
                if match.start() > last_end:
                    pre_text = solution[last_end:match.start()].strip()
                    if pre_text:
                        solution_blocks.append(pre_text)
                file_name = match.group(1).strip('`*, ')
                language = match.group(2).strip() or 'text'
                code = match.group(3)
                files.append({
                    'file_name': file_name,
                    'language': language,
                    'code': code
                })
                # Only add the code block (without file name header) to solution_blocks
                solution_blocks.append(f'```{language}\n{code}\n```')
                last_end = match.end()
            # Add any trailing text after the last code block
            if last_end < len(solution):
                trailing = solution[last_end:].strip()
                if trailing:
                    solution_blocks.append(trailing)
        # Parse run commands and packages
        def extract_bash_commands(section_list):
            commands = []
            for section in section_list:
                bash_commands = re.findall(r'```bash\s*\n(.*?)\n```', section, re.DOTALL)
                for cmd in bash_commands:
                    commands.extend([line.strip() for line in cmd.split('\n') if line.strip()])
            return commands
        packages = extract_bash_commands(sections["Required Packages"])
        run_commands = extract_bash_commands(sections["Run Commands"])
        # Return structured sections
        return {
            'analysis': sections["Analysis"],
            'packages': packages,
            'solution': "\n\n".join(solution_blocks),
            'run_commands': run_commands,
            'usage': sections["Usage Instructions"],
            'files': files
        }

# Initialize the model client
model_client = ModelAPIClient(DEFAULT_CONFIG)

@app.route('/api/analyze-and-execute', methods=['POST'])
def analyze_and_execute():
    def minimal_sections_response(analysis_msg):
        return {
            'analysis': analysis_msg,
            'packages': [],
            'solution': '',
            'run_commands': [],
            'usage': '',
            'files': []
        }

    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing prompt in request body'
            }), 400

        user_prompt = data['prompt']
        context = data.get('context', '')
        files = data.get('files', None)
        folders = data.get('folders', None)

        # --- Handle greetings and unclear prompts before any analysis ---
        prompt_lower = user_prompt.strip().lower()
        greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]
        unclear_phrases = [
            "i don't know", "not sure", "can't tell", "unable to", "don't understand", "unclear", "?", "help", "what", "who are you", "explain yourself"
        ]
        if any(prompt_lower == g for g in greetings):
            analysis_msg = "Hello! How can I assist you today?"
            return jsonify({
                'success': True,
                'type': 'analysis',
                'output': analysis_msg,
                'sections': minimal_sections_response(analysis_msg),
                'prompt': user_prompt,
                'context_tokens': 0,
                'total_analyzed': 0,
                'analyzed_files': [],
                'files': []
            })
        if (not user_prompt.strip() or len(user_prompt.strip()) < 3 or any(phrase in prompt_lower for phrase in unclear_phrases)):
            analysis_msg = "Sorry, I couldn't understand your request. Please provide more details."
            return jsonify({
                'success': True,
                'type': 'analysis',
                'output': analysis_msg,
                'sections': minimal_sections_response(analysis_msg),
                'prompt': user_prompt,
                'context_tokens': 0,
                'total_analyzed': 0,
                'analyzed_files': [],
                'files': []
            })

        # Initialize analyzer
        analyzer = ASTContextAnalyzer()
        analysis_results = []
        temp_files = []
        
        try:
            # Analyze folders if provided
            if folders:
                for folder_info in folders:
                    if 'path' in folder_info and os.path.exists(folder_info['path']):
                        folder_analysis = analyzer.analyze_folder_structure(folder_info['path'])
                        analysis_results.append({
                            'type': 'folder',
                            'data': folder_analysis
                        })
            
            # Analyze files if provided
            if files:
                for file_info in files:
                    # Support both {path, language} and {name, type, content}
                    if 'path' in file_info and os.path.exists(file_info['path']):
                        file_path = file_info['path']
                        language = file_info.get('language', 'unknown')
                        result = analyzer.analyze_file(file_path, language)
                        analysis_results.append({
                            'type': 'file',
                            'data': result
                        })
                    elif 'content' in file_info and 'name' in file_info:
                        # Save base64 content to a temp file
                        file_bytes = base64.b64decode(file_info['content'])
                        suffix = os.path.splitext(file_info['name'])[1]
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as tmp:
                            tmp.write(file_bytes)
                            temp_path = tmp.name
                        temp_files.append(temp_path)
                        # Guess language from extension
                        ext = suffix.lower()
                        language_map = {'.py': 'python', '.js': 'javascript', '.ts': 'typescript', '.html': 'html', '.css': 'css', '.json': 'json', '.yml': 'yaml', '.yaml': 'yaml', '.xml': 'xml'}
                        language = language_map.get(ext, 'unknown')
                        result = analyzer.analyze_file(temp_path, language)
                        analysis_results.append({
                            'type': 'file',
                            'data': result
                        })
            
            # Create optimized context with token awareness
            context_parts = []
            total_tokens = 0
            max_context_tokens = DEFAULT_CONFIG.get('maxInputTokens', 6000) - count_tokens(user_prompt) - 1000  # Reserve space for system prompt and response
            
            for result in analysis_results:
                if result['type'] == 'folder':
                    folder_data = result['data']
                    if 'error' not in folder_data:
                        folder_summary = f"📁 Folder: {folder_data.get('folder_path', '')}\n"
                        folder_summary += f"📊 {folder_data.get('summary', '')}\n"
                        folder_summary += f"📁 Directories: {folder_data.get('total_dirs', 0)}\n"
                        folder_summary += f"📄 Files: {folder_data.get('total_files', 0)}\n"
                        
                        # Add file type breakdown
                        for lang, count in folder_data.get('file_types', {}).items():
                            if count > 0:
                                folder_summary += f"  • {count} {lang} files\n"
                        
                        folder_tokens = count_tokens(folder_summary)
                        if total_tokens + folder_tokens <= max_context_tokens:
                            context_parts.append(folder_summary)
                            total_tokens += folder_tokens
                
                elif result['type'] == 'file':
                    file_data = result['data']
                    if 'error' not in file_data:
                        file_summary = f"📄 File: {file_data.get('file_path', file_data.get('name', ''))}\n"
                        file_summary += f"🔤 Language: {file_data.get('language', 'unknown')}\n"
                        
                        # Add structure information
                        if 'structure' in file_data:
                            file_summary += f"🏗️ Structure: {file_data['structure']}\n"
                        
                        # Add imports
                        if 'imports' in file_data and file_data['imports']:
                            imports_str = ', '.join(file_data['imports'][:3])  # Limit to 3 imports
                            file_summary += f"📦 Imports: {imports_str}\n"
                        
                        # Add functions/classes
                        if 'functions' in file_data and file_data['functions']:
                            func_names = []
                            for func in file_data['functions'][:3]:  # Limit to 3 functions
                                if isinstance(func, dict) and 'name' in func:
                                    func_names.append(func['name'])
                                elif isinstance(func, str):
                                    func_names.append(func)
                            if func_names:
                                file_summary += f"⚙️ Functions: {', '.join(func_names)}\n"
                        
                        # Add complexity metrics
                        if 'complexity' in file_data:
                            comp = file_data['complexity']
                            file_summary += f"📈 Complexity: {comp.get('function_count', 0)} functions, {comp.get('class_count', 0)} classes, max nesting: {comp.get('max_nesting', 0)}\n"
                        
                        # Add main program if available
                        if 'main_program' in file_data and file_data['main_program']:
                            main_program = file_data['main_program']
                            # Limit main program to reasonable size
                            if len(main_program) > 500:
                                main_program = main_program[:500] + "\n# ... (truncated)"
                            file_summary += f"🚀 Main Program:\n```{file_data.get('language', 'text')}\n{main_program}\n```\n"
                        
                        # Add token count
                        if 'token_count' in file_data:
                            file_summary += f"🔢 Tokens: {file_data['token_count']}\n"
                        
                        file_tokens = count_tokens(file_summary)
                        if total_tokens + file_tokens <= max_context_tokens:
                            context_parts.append(file_summary)
                            total_tokens += file_tokens
                        else:
                            # Add a truncated version
                            truncated_summary = f"📄 File: {file_data.get('file_path', file_data.get('name', ''))} ({file_data.get('language', 'unknown')}) - {file_data.get('token_count', 0)} tokens\n"
                            truncated_tokens = count_tokens(truncated_summary)
                            if total_tokens + truncated_tokens <= max_context_tokens:
                                context_parts.append(truncated_summary)
                                total_tokens += truncated_tokens
            
            # Combine context parts
            optimized_context = '\n\n'.join(context_parts)
            context = optimized_context
            
        finally:
            # Clean up temp files
            for temp_path in temp_files:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

        # Generate comprehensive response with analyze-think-execute approach
        model_output = model_client.generate_full_response(user_prompt, context)

        # Parse the response into structured sections
        try:
            sections = model_client.parse_response_sections(model_output)
        except Exception as parse_error:
            analysis_msg = f"Sorry, I was unable to process the model's response. ({str(parse_error)})"
            return jsonify({
                'success': True,
                'type': 'analysis',
                'output': analysis_msg,
                'sections': minimal_sections_response(analysis_msg),
                'prompt': user_prompt,
                'context_tokens': 0,
                'total_analyzed': 0,
                'analyzed_files': [],
                'files': []
            })

        # If the model_output is an error message (starts with 'Error:'), handle gracefully
        if isinstance(model_output, str) and model_output.strip().lower().startswith('error:'):
            analysis_msg = f"Sorry, I was unable to generate a response for your request. {model_output}"
            return jsonify({
                'success': True,
                'type': 'analysis',
                'output': analysis_msg,
                'sections': minimal_sections_response(analysis_msg),
                'prompt': user_prompt,
                'context_tokens': 0,
                'total_analyzed': 0,
                'analyzed_files': [],
                'files': []
            })

        # Collect file information for response
        analyzed_files = []
        for result in analysis_results:
            if result['type'] == 'file':
                file_data = result['data']
                file_info = {
                    'name': file_data.get('file_path', file_data.get('name', '')),
                    'language': file_data.get('language', 'unknown'),
                    'token_count': file_data.get('token_count', 0),
                    'lines': file_data.get('lines', 0),
                    'structure': file_data.get('structure', ''),
                    'error': file_data.get('error', None)
                }
                analyzed_files.append(file_info)
            elif result['type'] == 'folder':
                folder_data = result['data']
                folder_info = {
                    'name': folder_data.get('folder_path', ''),
                    'type': 'folder',
                    'total_files': folder_data.get('total_files', 0),
                    'total_dirs': folder_data.get('total_dirs', 0),
                    'summary': folder_data.get('summary', ''),
                    'error': folder_data.get('error', None)
                }
                analyzed_files.append(folder_info)
        print(sections)

        
        print(model_output)
        return jsonify({
            'success': True,
            'type': 'analysis',
            'output': model_output,
            'sections': sections,
            'prompt': user_prompt,
            'context_tokens': count_tokens(context),
            'total_analyzed': len(analysis_results),
            'analyzed_files': analyzed_files,
            'files': sections.get('files', [])  # New: add files array to response
        })
    except Exception as error:
        print(error)
        return jsonify({
            'success': False,
            'error': f'Server error: {str(error)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Flask backend is running'
    })

if __name__ == '__main__':
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    
    print(f"Starting Flask backend on port {port}")
    print(f"Model API URL: {DEFAULT_CONFIG['modelApiUrl']}")
    print(f"Model: {DEFAULT_CONFIG['model']}")
    print(f"Max context length: {DEFAULT_CONFIG['maxContextLength']}")
    
    app.run(host='0.0.0.0', port=port, debug=True) 
