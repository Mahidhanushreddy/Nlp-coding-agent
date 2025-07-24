"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const nlp_agent_1 = require("./nlp-agent");
const axios_1 = __importDefault(require("axios"));
const child_process = __importStar(require("child_process"));
const path = __importStar(require("path"));
// Default configuration
const defaultConfig = {
    modelApiUrl: 'https://api.groq.com/openai/v1/chat/completions',
    apiKey: 'Bearer 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',
    maxRetries: 3,
    timeout: 30000,
    model: 'llama3-8b-8192',
    backendUrl: 'http://localhost:5000'
};
let nlpAgent;
// Dedicated terminal for all executions
let nlpAgentTerminal;
function getOrCreateNlpAgentTerminal() {
    if (!nlpAgentTerminal || nlpAgentTerminal.exitStatus) {
        nlpAgentTerminal = vscode.window.createTerminal({ name: 'NLP Agent Terminal', hideFromUser: false });
    }
    nlpAgentTerminal.show();
    return nlpAgentTerminal;
}
function activate(context) {
    console.log('NLP Coding Agent extension is now active!');
    // --- Auto-start Flask backend if not running ---
    const backendUrl = defaultConfig.backendUrl || 'http://localhost:5000';
    const healthUrl = `${backendUrl}/api/health`;
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';
    const extensionRoot = __dirname.includes('out') ? path.resolve(__dirname, '..') : __dirname;
    async function ensureBackendRunning() {
        try {
            // Try health check first
            const res = await axios_1.default.get(healthUrl, { timeout: 3000 });
            if (res.status === 200) {
                console.log('Flask backend already running.');
                return;
            }
        }
        catch (e) {
            // Not running, so start it
            let scriptPath = '';
            let spawnCmd = '';
            let spawnArgs = [];
            let options = { cwd: extensionRoot, detached: true, shell: true };
            if (process.platform === 'win32') {
                scriptPath = path.join(extensionRoot, 'start-flask-backend.bat');
                spawnCmd = 'cmd.exe';
                spawnArgs = ['/c', scriptPath];
            }
            else {
                scriptPath = path.join(extensionRoot, 'start-flask-backend.sh');
                spawnCmd = 'bash';
                spawnArgs = [scriptPath];
            }
            try {
                const child = child_process.spawn(spawnCmd, spawnArgs, options);
                child.unref();
                console.log('Started Flask backend process.');
                vscode.window.showInformationMessage('Starting Flask backend for NLP Agent...');
                // Wait a few seconds for backend to start
                await new Promise(res => setTimeout(res, 4000));
            }
            catch (err) {
                vscode.window.showErrorMessage('Failed to start Flask backend: ' + err);
            }
        }
    }
    // Ensure backend is running before anything else
    ensureBackendRunning();
    // --- End auto-start logic ---
    // Initialize the NLP agent
    nlpAgent = new nlp_agent_1.NLPAgent(context, defaultConfig);
    // Register commands
    let executeCommand = vscode.commands.registerCommand('nlp-agent.executeCommand', async () => {
        await handleExecuteCommand();
    });
    let interactiveMode = vscode.commands.registerCommand('nlp-agent.interactiveMode', async () => {
        await handleInteractiveMode();
    });
    context.subscriptions.push(executeCommand, interactiveMode);
}
async function handleExecuteCommand() {
    try {
        const prompt = await vscode.window.showInputBox({
            prompt: 'Enter your request:',
            placeHolder: 'e.g., create a web app, build a data visualization, generate a React component'
        });
        if (!prompt) {
            return;
        }
        // Get VSCode context for better analysis
        const vsContext = getVSCodeContext();
        // Use the intelligent analyze-and-execute method with context
        const result = await nlpAgent.analyzeAndExecute(prompt, vsContext);
        console.log(result);
        if (result.success) {
            if (result.type === 'analysis' && result.output) {
                // Show analysis response in a new document
                const document = await vscode.workspace.openTextDocument({
                    content: result.output,
                    language: 'markdown'
                });
                await vscode.window.showTextDocument(document);
                vscode.window.showInformationMessage(`📝 Analysis completed and opened in new document`);
            }
        }
        else {
            vscode.window.showErrorMessage(`❌ ${result.error}`);
        }
    }
    catch (error) {
        vscode.window.showErrorMessage(`Error: ${error}`);
    }
}
async function handleInteractiveMode() {
    try {
        const panel = vscode.window.createWebviewPanel('nlpAgent', 'NLP Coding Agent', vscode.ViewColumn.One, {
            enableScripts: true,
            retainContextWhenHidden: true
        });
        panel.webview.html = getWebviewContent();
        panel.webview.onDidReceiveMessage(async (message) => {
            if (message.command === 'execute') {
                // Get VSCode context for better analysis
                const vsContext = getVSCodeContext();
                const result = await nlpAgent.analyzeAndExecute(message.text, vsContext, message.files);
                panel.webview.postMessage({
                    command: 'result',
                    success: result.success,
                    type: result.type,
                    output: result.output,
                    sections: result.sections,
                    error: result.error,
                    files: result.files // <-- add this line
                });
            }
            else if (message.command === 'runCommand') {
                // Execute command in terminal with enhanced functionality
                await executeCommandInTerminal(message.shellCommand);
            }
            else if (message.command === 'runProgram') {
                // Execute a program (file) in terminal
                await executeProgramInTerminal(message.filePath, message.language);
            }
            else if (message.command === 'createAndRunFile') {
                // Create a file with content and then run it
                await createAndRunFile(message.fileName, message.content, message.language);
            }
            else if (message.command === 'selectFolder') {
                const folderUris = await vscode.window.showOpenDialog({
                    canSelectFiles: false,
                    canSelectFolders: true,
                    canSelectMany: false,
                    openLabel: 'Select Folder',
                    title: 'Select Folder for Files'
                });
                if (folderUris && folderUris.length > 0) {
                    const folderUri = folderUris[0];
                    const folderPath = folderUri.fsPath;
                    const files = [];
                    const fs = require('fs');
                    const path = require('path');
                    function walk(dir, rel) {
                        const entries = fs.readdirSync(dir, { withFileTypes: true });
                        for (const entry of entries) {
                            const entryPath = path.join(dir, entry.name);
                            const relPath = path.join(rel, entry.name);
                            if (entry.isDirectory()) {
                                walk(entryPath, relPath);
                            }
                            else if (entry.isFile()) {
                                try {
                                    const content = fs.readFileSync(entryPath);
                                    files.push({
                                        name: entry.name,
                                        relativePath: relPath,
                                        type: 'file',
                                        size: content.length,
                                        content: content.toString('base64')
                                    });
                                }
                                catch (e) {
                                    // skip unreadable files
                                }
                            }
                        }
                    }
                    walk(folderPath, '');
                    panel.webview.postMessage({ command: 'folderFiles', files });
                }
            }
        }, undefined, []);
    }
    catch (error) {
        vscode.window.showErrorMessage(`Error starting interactive mode: ${error}`);
    }
}
function getVSCodeContext() {
    const editor = vscode.window.activeTextEditor;
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';
    return {
        workspaceRoot,
        activeEditor: editor,
        selectedText: editor?.document.getText(editor.selection),
        currentFile: editor?.document.fileName,
        language: editor?.document.languageId
    };
}
async function executeCommandInTerminal(command) {
    try {
        const terminal = getOrCreateNlpAgentTerminal();
        terminal.sendText(command, true);
        vscode.window.showInformationMessage(`🚀 Command executed: ${command}`);
    }
    catch (error) {
        vscode.window.showErrorMessage(`❌ Failed to execute command: ${error}`);
    }
}
async function executeProgramInTerminal(filePath, language) {
    try {
        const terminal = getOrCreateNlpAgentTerminal();
        // Determine the appropriate command based on language
        let runCommand = '';
        switch (language.toLowerCase()) {
            case 'python':
                runCommand = `python "${filePath}"`;
                break;
            case 'javascript':
            case 'js':
                runCommand = `node "${filePath}"`;
                break;
            case 'typescript':
            case 'ts':
                runCommand = `npx ts-node "${filePath}"`;
                break;
            case 'html':
                runCommand = `start "${filePath}"`;
                break;
            case 'java':
                runCommand = `java "${filePath}"`;
                break;
            case 'cpp':
            case 'c++':
                runCommand = `g++ "${filePath}" -o "${filePath}.exe" && "${filePath}.exe"`;
                break;
            case 'c':
                runCommand = `gcc "${filePath}" -o "${filePath}.exe" && "${filePath}.exe"`;
                break;
            default:
                runCommand = `"${filePath}"`;
        }
        terminal.sendText(runCommand, true);
        vscode.window.showInformationMessage(`🚀 Program executed: ${runCommand}`);
    }
    catch (error) {
        vscode.window.showErrorMessage(`❌ Failed to execute program: ${error}`);
    }
}
async function createAndRunFile(fileName, content, language) {
    try {
        const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
        if (!workspaceRoot) {
            throw new Error('No workspace folder found');
        }
        // Create the file path
        const filePath = vscode.Uri.file(path.join(workspaceRoot, fileName));
        // Write content to file
        const writeData = Buffer.from(content, 'utf8');
        await vscode.workspace.fs.writeFile(filePath, writeData);
        // Open the file in editor
        const document = await vscode.workspace.openTextDocument(filePath);
        await vscode.window.showTextDocument(document);
        // Execute the file
        await executeProgramInTerminal(filePath.fsPath, language);
        vscode.window.showInformationMessage(`✅ File created and executed: ${fileName}`);
    }
    catch (error) {
        vscode.window.showErrorMessage(`❌ Failed to create and run file: ${error}`);
    }
}
function getWebviewContent() {
    return '<!DOCTYPE html>' +
        '<html lang="en">' +
        '<head>' +
        '<meta charset="UTF-8">' +
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">' +
        '<title>NLP Coding Agent</title>' +
        '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">' +
        '<style>' +
        'body {' +
        'font-family: "Fira Mono", "Consolas", "Menlo", "Monaco", "monospace", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;' +
        'padding: 0;' +
        'margin: 0;' +
        'background-color: #181c20;' +
        'color: #d4d4d4;' +
        '}' +
        '.container {' +
        'max-width: 900px;' +
        'margin: 0 auto;' +
        'padding: 32px 16px 16px 16px;' +
        '}' +
        '.input-group {' +
        'margin-bottom: 20px;' +
        '}' +
        '.input-group textarea {' +
        'width: 100%;' +
        'padding: 12px;' +
        'border: 1px solid #333;' +
        'background-color: #23272e;' +
        'color: #d4d4d4;' +
        'border-radius: 4px;' +
        'font-size: 15px;' +
        'resize: vertical;' +
        'min-height: 70px;' +
        'max-height: 300px;' +
        '}' +
        '.action-row {' +
        'display: flex;' +
        'gap: 10px;' +
        'align-items: center;' +
        'margin-top: 10px;' +
        '}' +
        'input[type="text"] {' +
        'width: 100%;' +
        'padding: 12px;' +
        'border: 1px solid #333;' +
        'background-color: #23272e;' +
        'color: #d4d4d4;' +
        'border-radius: 4px;' +
        'font-size: 15px;' +
        '}' +
        'button {' +
        'background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);' +
        'color: #fff;' +
        'border: none;' +
        'padding: 12px 24px;' +
        'border-radius: 6px;' +
        'cursor: pointer;' +
        'font-size: 15px;' +
        'font-weight: 600;' +
        'transition: all 0.3s ease;' +
        'box-shadow: 0 2px 8px rgba(66, 153, 225, 0.3);' +
        '}' +
        'button:hover {' +
        'background: linear-gradient(135deg, #3182ce 0%, #2b6cb0 100%);' +
        'transform: translateY(-1px);' +
        'box-shadow: 0 4px 12px rgba(66, 153, 225, 0.4);' +
        '}' +
        '.run-btn {' +
        'background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);' +
        'padding: 8px 16px;' +
        'font-size: 13px;' +
        'margin-left: 10px;' +
        '}' +
        '.run-btn:hover {' +
        'background: linear-gradient(135deg, #38a169 0%, #2f855a 100%);' +
        '}' +
        '.section {' +
        'margin-bottom: 24px;' +
        'padding: 20px;' +
        'background: linear-gradient(135deg, #1e2127 0%, #2d3748 100%);' +
        'border-radius: 8px;' +
        'border: 1px solid #3a3f4b;' +
        '}' +
        '.section-title {' +
        'font-size: 1.2em;' +
        'font-weight: 600;' +
        'margin-bottom: 12px;' +
        'color: #4299e1;' +
        '}' +
        '.package-item, .command-item {' +
        'display: flex;' +
        'align-items: center;' +
        'justify-content: space-between;' +
        'padding: 8px 12px;' +
        'background: rgba(66, 153, 225, 0.1);' +
        'border-radius: 4px;' +
        'margin-bottom: 8px;' +
        'border: 1px solid rgba(66, 153, 225, 0.2);' +
        '}' +
        '.command-text {' +
        'font-family: "Fira Mono", monospace;' +
        'color: #e6fffa;' +
        'flex: 1;' +
        '}' +
        '.output {' +
        'margin-top: 24px;' +
        'padding: 0;' +
        'border-radius: 8px;' +
        'background: linear-gradient(135deg, #1e2127 0%, #2d3748 100%);' +
        'box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);' +
        'font-size: 15px;' +
        'border: 1px solid #3a3f4b;' +
        'overflow: hidden;' +
        '}' +
        '.code-block {' +
        'position: relative;' +
        'margin: 0;' +
        'margin-bottom: 20px;' +
        'background: linear-gradient(145deg, #0f1419 0%, #1a1f2e 100%);' +
        'border-radius: 8px;' +
        'overflow: auto;' +
        'box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);' +
        'border: 1px solid #2d3748;' +
        '}' +
        'pre {' +
        'margin: 0;' +
        'padding: 20px 18px 18px 50px;' +
        'font-size: 15px;' +
        'line-height: 1.6;' +
        'background: transparent;' +
        '}' +
        '.copy-btn {' +
        'position: absolute;' +
        'top: 14px;' +
        'right: 18px;' +
        'background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%);' +
        'color: #fff;' +
        'border: 1px solid #4a5568;' +
        'border-radius: 6px;' +
        'padding: 6px 14px;' +
        'font-size: 13px;' +
        'cursor: pointer;' +
        'z-index: 2;' +
        'opacity: 0.9;' +
        'transition: all 0.3s ease;' +
        'font-weight: 500;' +
        '}' +
        '.copy-btn:hover {' +
        'background: linear-gradient(135deg, #3182ce 0%, #4299e1 100%);' +
        'opacity: 1;' +
        'transform: translateY(-1px);' +
        'box-shadow: 0 2px 8px rgba(49, 130, 206, 0.3);' +
        '}' +
        '.code-block .run-btn {' +
        'position: absolute;' +
        'top: 14px;' +
        'right: 80px;' +
        'background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);' +
        'color: #fff;' +
        'border: 1px solid #38a169;' +
        'border-radius: 6px;' +
        'padding: 6px 14px;' +
        'font-size: 13px;' +
        'cursor: pointer;' +
        'z-index: 2;' +
        'opacity: 0.9;' +
        'transition: all 0.3s ease;' +
        'font-weight: 500;' +
        '}' +
        '.code-block .run-btn:hover {' +
        'background: linear-gradient(135deg, #38a169 0%, #2f855a 100%);' +
        'opacity: 1;' +
        'transform: translateY(-1px);' +
        'box-shadow: 0 2px 8px rgba(56, 161, 105, 0.3);' +
        '}' +
        '.hljs {' +
        'background: none;' +
        '}' +
        '.editor-title {' +
        'font-size: 1.7em;' +
        'font-weight: 700;' +
        'margin-bottom: 8px;' +
        'color: #4299e1;' +
        'text-shadow: 0 2px 4px rgba(66, 153, 225, 0.3);' +
        '}' +
        '.text-content {' +
        'padding: 20px 24px;' +
        'background: linear-gradient(135deg, #0a1419 0%, #1a2f2e 50%, #2a4a4a 100%);' +
        'border-radius: 8px;' +
        'margin: 0;' +
        'line-height: 1.7;' +
        'color: #e6fffa;' +
        'border: 1px solid #38a169;' +
        '}' +
        '.success-output {' +
        'border-left: 4px solid #48bb78;' +
        'background: linear-gradient(135deg, #0a1419 0%, #1a2f2e 50%, #2a4a4a 100%);' +
        '}' +
        '.error-output {' +
        'border-left: 4px solid #f56565;' +
        'background: linear-gradient(135deg, #2d1b1b 0%, #3d2a2a 100%);' +
        '}' +
        '.info-output {' +
        'border-left: 4px solid #4299e1;' +
        'background: linear-gradient(135deg, #0a1419 0%, #1a2f2e 50%, #2a4a4a 100%);' +
        '}' +
        '.upload-btn {' +
        'background: linear-gradient(135deg, #22543d 0%, #276749 100%);' +
        'color: #fff;' +
        'border: none;' +
        'padding: 10px 22px;' +
        'border-radius: 6px;' +
        'cursor: pointer;' +
        'font-size: 15px;' +
        'font-weight: 600;' +
        'margin-bottom: 6px;' +
        'margin-right: 10px;' +
        'transition: all 0.3s ease;' +
        'box-shadow: 0 2px 8px rgba(34, 84, 61, 0.2);' +
        '}' +
        '.upload-btn:hover {' +
        'background: linear-gradient(135deg, #276749 0%, #22543d 100%);' +
        'transform: translateY(-1px);' +
        'box-shadow: 0 4px 12px rgba(34, 84, 61, 0.3);' +
        '}' +
        '.selected-files {' +
        'color: #b794f4;' +
        'font-size: 13px;' +
        'margin-top: 4px;' +
        'margin-bottom: 2px;' +
        'min-height: 18px;' +
        '}' +
        '.delete-btn {' +
        'background: linear-gradient(135deg, #e53e3e 0%, #c53030 100%);' +
        'color: #fff;' +
        'border: none;' +
        'padding: 8px 16px;' +
        'border-radius: 6px;' +
        'cursor: pointer;' +
        'font-size: 13px;' +
        'font-weight: 600;' +
        'margin-left: 10px;' +
        'transition: all 0.3s ease;' +
        '}' +
        '.delete-btn:hover {' +
        'background: linear-gradient(135deg, #c53030 0%, #9b2c2c 100%);' +
        '}' +
        '.file-label {' +
        'font-size: 1em;' +
        'font-weight: 600;' +
        'color:rgb(148, 244, 175);' +
        'margin-bottom: 6px;' +
        'margin-left: 8px;' +
        '}' +
        '</style>' +
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>' +
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js"></script>' +
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/javascript.min.js"></script>' +
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/typescript.min.js"></script>' +
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/bash.min.js"></script>' +
        '</head>' +
        '<body>' +
        '<div class="container">' +
        '<div class="editor-title">🤖 NLP Coding Agent</div>' +
        '<p>Ask me to analyze, think, and execute coding tasks with complete solutions!</p>' +
        '<div class="input-group">' +
        '<textarea id="promptInput" placeholder="e.g., create a web app, build a data visualization, generate a React component"></textarea>' +
        '<div style="margin-top:10px; display: flex; align-items: center; gap: 10px;">' +
        '<input type="file" id="fileInput" multiple style="display:none;">' +
        '<button id="uploadBtn" type="button" class="upload-btn">Upload Files</button>' +
        '</div>' +
        '</div>' +
        '<div id="selectedFilesContainer" style="margin-bottom: 16px; display:none;">' +
        '<div id="selectedFiles" class="selected-files"></div>' +
        '</div>' +
        '<div class="action-row">' +
        '<button onclick="executeAction()">Run</button>' +
        '</div>' +
        '<div id="output" class="output" style="display: none;"></div>' +
        '</div>' +
        '<script>' +
        'const vscode = acquireVsCodeApi();' +
        'let selectedFiles = [];' +
        'let codeBlocks = [];' +
        'let fileInfos = [];' +
        'function updateSelectedFilesUI() {' +
        'const container = document.getElementById("selectedFilesContainer");' +
        'const filesDiv = document.getElementById("selectedFiles");' +
        'let html = "";' +
        'selectedFiles.forEach((f, idx) => {' +
        'html += `<div style=\"display:flex;align-items:center;\">`;' +
        'html += `<span>${f.name}</span>`;' +
        'html += `<button class=\"delete-btn\" data-file-idx=\"${idx}\" style=\"margin-left:10px;\">Delete</button>`;' +
        'html += `</div>`;' +
        '});' +
        'if (selectedFiles.length > 0) {' +
        'container.style.display = "block";' +
        'filesDiv.innerHTML = html;' +
        '} else {' +
        'container.style.display = "none";' +
        'filesDiv.innerHTML = "";' +
        '}' +
        'setTimeout(() => {' +
        'document.querySelectorAll(".delete-btn[data-file-idx]").forEach(btn => {' +
        'btn.onclick = function() {' +
        'const idx = parseInt(btn.getAttribute("data-file-idx"), 10);' +
        'if (!isNaN(idx)) {' +
        'selectedFiles.splice(idx, 1);' +
        'updateSelectedFilesUI();' +
        '}' +
        '};' +
        '});' +
        '}, 10);' +
        '}' +
        'document.getElementById("uploadBtn").addEventListener("click", function() {' +
        'document.getElementById("fileInput").value = "";' +
        'document.getElementById("fileInput").click();' +
        '});' +
        'document.getElementById("fileInput").addEventListener("change", function(e) {' +
        'const files = Array.from(e.target.files);' +
        'const fileReaders = files.map(file => new Promise(resolve => {' +
        'const reader = new FileReader();' +
        'reader.onload = function(ev) {' +
        'const exists = selectedFiles.some(function(f) {' +
        'return (f.name === file.name && f.size === file.size);' +
        '});' +
        'if (!exists) {' +
        'selectedFiles.push({' +
        'name: file.name,' +
        'type: file.type,' +
        'size: file.size,' +
        'content: reader.result.split(",")[1],' +
        'relativePath: file.name' +
        '});' +
        '}' +
        'resolve();' +
        '};' +
        'reader.readAsDataURL(file);' +
        '}));' +
        'Promise.all(fileReaders).then(updateSelectedFilesUI);' +
        '});' +
        '' +
        'function executeAction() {' +
        'const input = document.getElementById("promptInput");' +
        'const text = input.value.trim();' +
        'if (text) {' +
        'vscode.postMessage({' +
        'command: "execute",' +
        'text: text,' +
        'files: selectedFiles' +
        '});' +
        'input.value = "";' +
        'selectedFiles = [];' +
        'document.getElementById("fileInput").value = "";' +
        'updateSelectedFilesUI();' +
        'showOutput("Analyzing and processing...", "info");' +
        '}' +
        '}' +
        '' +
        'function runCommand(command) {' +
        'vscode.postMessage({' +
        'command: "runCommand",' +
        'shellCommand: command' +
        '});' +
        '}' +
        '' +
        'function runProgram(filePath, language) {' +
        'vscode.postMessage({' +
        'command: "runProgram",' +
        'filePath: filePath,' +
        'language: language' +
        '});' +
        '}' +
        '' +
        'function createAndRunFile(fileName, content, language) {' +
        'vscode.postMessage({' +
        'command: "createAndRunFile",' +
        'fileName: fileName,' +
        'content: content,' +
        'language: language' +
        '});' +
        '}' +
        '' +
        'function escapeHtml(str) {' +
        'return str.replace(/[&<>]/g, tag => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[tag]));' +
        '}' +
        '' +
        'function parseAndRenderBlocks(content, filesFromBackend) {' +
        'const codeBlockRegex = /```([a-zA-Z0-9]*)\\n([\\s\\S]*?)```/g;' +
        'let lastIndex = 0;' +
        'let match;' +
        'let html = "";' +
        'let blockIdx = 0;' +
        'codeBlocks = [];' + // Reset code blocks for each render
        'fileInfos = filesFromBackend || [];console.log(fileInfos);' +
        '' +
        'while ((match = codeBlockRegex.exec(content)) !== null) {' +
        'if (match.index > lastIndex) {' +
        'const textContent = content.slice(lastIndex, match.index);' +
        'if (textContent.trim().length > 0) {' +
        'html += "<div class=\\"text-content\\">" + ' +
        'escapeHtml(textContent).replace(/\\n/g, "<br>") + ' +
        '"</div>";' +
        '}' +
        '}' +
        '' +
        'const lang = match[1] || "";' +
        'const code = match[2];' +
        'codeBlocks.push(code);' + // Store raw code
        '' +
        'if (code.trim().length > 0) {' +
        'let runButton = "";' +
        'let fileNameLabel = "";' +
        'if (Array.isArray(fileInfos) && fileInfos[blockIdx] && fileInfos[blockIdx].file_name) {' +
        'const fileName = fileInfos[blockIdx].file_name;' +
        'const language = fileInfos[blockIdx].language || lang;' +
        'fileNameLabel = `<div class=\\"file-label\\"><b>${escapeHtml(fileName)}</b></div>`;' +
        'runButton = `<button class=\\"run-btn\\" data-filename=\\"${fileName}\\" data-code-idx=\\"${blockIdx}\\" data-language=\\"${language}\\">Run</button>`;' +
        '} else {' +
        'const ext = lang.toLowerCase() || "txt";' +
        'fileNameLabel = `<div class=\\"file-label\\"><b>script${blockIdx}.${ext}</b></div>`;' +
        'runButton = `<button class=\\"run-btn\\" data-filename=\\"script${blockIdx}.${ext}\\" data-code-idx=\\"${blockIdx}\\" data-language=\\"${lang}\\">Run</button>`;' +
        '}' +
        'html += fileNameLabel +' +
        '"<div class=\\"code-block\\">" +' +
        '"<button class=\\"copy-btn\\" data-idx=\\"" + blockIdx + "\\">Copy</button>" + runButton +' +
        '"<pre><code class=\\"hljs " + lang + "\\">" + escapeHtml(code) + "</code></pre>" +' +
        '"</div>";' +
        '}' +
        '' +
        'lastIndex = codeBlockRegex.lastIndex;' +
        'blockIdx++;' +
        '}' +
        '' +
        'if (lastIndex < content.length) {' +
        'const trailingText = content.slice(lastIndex);' +
        'if (trailingText.trim().length > 0) {' +
        'html += "<div class=\\"text-content\\">" + ' +
        'escapeHtml(trailingText).replace(/\\n/g, "<br>") + ' +
        '"</div>";' +
        '}' +
        '}' +
        '' +
        'return html;' +
        '}' +
        '' +
        'function renderSections(sections, filesFromBackend) {' +
        'let html = "";' +
        '' +
        'if (sections.analysis) {' +
        'html += "<div class=\\"section\\">" +' +
        '"<div class=\\"section-title\\">Analysis</div>" +' +
        '"<div class=\\"text-content\\">" + escapeHtml(sections.analysis).replace(/\\n/g, "<br>") + "</div>" +' +
        '"</div>";' +
        '}' +
        '' +
        'if (sections.packages && sections.packages.length > 0) {' +
        'html += "<div class=\\"section\\">" +' +
        '"<div class=\\"section-title\\">Required Packages</div>";' +
        'sections.packages.forEach(pkg => {' +
        'const isComment = pkg.trim().startsWith("#") || pkg.trim().startsWith("//") || pkg.trim().startsWith("/*") || pkg.trim().startsWith("*");' +
        'if (isComment) {' +
        'html += "<div style=\\"margin-bottom: 6px;\\">" +' +
        '"<span class=\\"command-text\\" style=\\"font-style: italic;\\">" + escapeHtml(pkg) + "</span>" +' +
        '"</div>";' +
        '} else {' +
        'html += "<div class=\\"package-item\\">" +' +
        '"<span class=\\"command-text\\">" + escapeHtml(pkg) + "</span>" +' +
        '`<button class=\\"run-btn\\" data-command=\\"${escapeHtml(pkg)}\\">Run</button>` +' +
        '"</div>";' +
        '}' +
        '});' +
        'html += "</div>";' +
        '}' +
        '' +
        'if (sections.solution) {' +
        'html += "<div class=\\"section\\">" +' +
        '"<div class=\\"section-title\\">Solution</div>" +' +
        'parseAndRenderBlocks(sections.solution, filesFromBackend) +' +
        '"</div>";' +
        '}' +
        '' +
        'if (sections.run_commands && sections.run_commands.length > 0) {' +
        'html += "<div class=\\"section\\">" +' +
        '"<div class=\\"section-title\\">Run Commands</div>";' +
        'sections.run_commands.forEach(cmd => {' +
        'const isComment = cmd.trim().startsWith("#") || cmd.trim().startsWith("//") || cmd.trim().startsWith("/*") || cmd.trim().startsWith("*");' +
        'if (isComment) {' +
        'html += "<div style=\\"margin-bottom: 6px;\\">" +' +
        '"<span class=\\"command-text\\" style=\\"font-style: italic\\">" + escapeHtml(cmd) + "</span>" +' +
        '"</div>";' +
        '} else {' +
        'html += "<div class=\\"command-item\\">" +' +
        '"<span class=\\"command-text\\">" + escapeHtml(cmd) + "</span>" +' +
        '`<button class=\\"run-btn\\" data-command=\\"${escapeHtml(cmd)}\\">Run</button>` +' +
        '"</div>";' +
        '}' +
        '});' +
        'html += "</div>";' +
        '}' +
        '' +
        'if (sections.usage) {' +
        'html += "<div class=\\"section\\">" +' +
        '"<div class=\\"section-title\\">Usage Instructions</div>" +' +
        '"<div class=\\"text-content\\">" + escapeHtml(sections.usage).replace(/\\n/g, "<br>") + "</div>" +' +
        '"</div>";' +
        '}' +
        '' +
        'return html;' +
        '}' +
        '' +
        'function showOutput(content, type, sections, filesFromBackend) {' +
        'const output = document.getElementById("output");' +
        'let html = "";' +
        '' +
        'if (type === "success" || type === "info") {' +
        'if (sections) {' +
        'html = renderSections(sections, filesFromBackend);' +
        '} else {' +
        'html = parseAndRenderBlocks(content);' +
        '}' +
        '} else if (type === "error") {' +
        'html = "<div class=\\"text-content error-output\\" style=\\"color:#f56565;\\">" + escapeHtml(content) + "</div>";' +
        '}' +
        '' +
        'output.innerHTML = html;' +
        'output.className = "output " + type + "-output";' +
        'output.style.display = "block";' +
        '' +
        'document.querySelectorAll("pre code").forEach(block => {' +
        'window.hljs.highlightElement(block);' +
        '});' +
        '' +
        'document.querySelectorAll(".copy-btn").forEach((btn, idx) => {' +
        'btn.onclick = function() {' +
        'const code = btn.parentElement.querySelector("code").innerText;' +
        'navigator.clipboard.writeText(code).then(() => {' +
        'btn.innerText = "Copied!";' +
        'setTimeout(() => { btn.innerText = "Copy"; }, 1200);' +
        '});' +
        '};' +
        '});' +
        // Attach run button listeners
        'document.querySelectorAll(".run-btn").forEach((btn) => {' +
        'if (btn.hasAttribute("data-command")) {' +
        'btn.onclick = function () {' +
        'const command = btn.getAttribute("data-command");' +
        'runCommand(command);' +
        '};' +
        '} else if (btn.hasAttribute("data-filename") && btn.hasAttribute("data-code-idx") && btn.hasAttribute("data-language")) {' +
        'btn.onclick = function () {' +
        'const fileName = btn.getAttribute("data-filename");' +
        'const codeIdx = parseInt(btn.getAttribute("data-code-idx"), 10);' +
        'const language = btn.getAttribute("data-language");' +
        'const content = codeBlocks[codeIdx];' + // Use raw code
        'createAndRunFile(fileName, content, language);' +
        '};' +
        '}' +
        '});' +
        '}' +
        '' +
        'document.getElementById("promptInput").addEventListener("keypress", function(e) {' +
        'if (e.key === "Enter" && !e.shiftKey) {' +
        'e.preventDefault();' +
        'executeAction();' +
        '}' +
        '});' +
        '' +
        'window.addEventListener("message", event => {' +
        'const message = event.data;' +
        '' +
        'if (message.command === "folderFiles") {' +
        'selectedFiles = message.files;' +
        'updateSelectedFilesUI();' +
        '} else if (message.command === "result") {' +
        'if (message.success) {' +
        'if (message.sections) {' +
        'showOutput("", "success", message.sections, message.files);' +
        '} else {' +
        'showOutput(message.output, "success");' +
        '}' +
        '} else {' +
        'showOutput(message.error, "error");' +
        '}' +
        '}' +
        '});' +
        '</script>' +
        '</body>' +
        '</html>';
}
function deactivate() {
    console.log('NLP Coding Agent extension is now deactivated!');
}
//# sourceMappingURL=extension.js.map