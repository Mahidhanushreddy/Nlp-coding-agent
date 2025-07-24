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
Object.defineProperty(exports, "__esModule", { value: true });
exports.NLPAgent = void 0;
const backend_client_1 = require("./backend-client");
const vscode = __importStar(require("vscode"));
class NLPAgent {
    constructor(context, config) {
        this.context = context;
        this.config = config;
        // Use backend URL if provided, otherwise default to localhost:5000
        const backendUrl = config.backendUrl || 'http://localhost:5000';
        this.backendClient = new backend_client_1.BackendClient({
            backendUrl: backendUrl,
            timeout: config.timeout
        });
    }
    async analyzeAndExecute(userPrompt, vsContext, files) {
        try {
            vscode.window.showInformationMessage(`🤖 Analyzing: "${userPrompt}"`);
            // Check if backend is available
            const isHealthy = await this.backendClient.healthCheck();
            if (!isHealthy) {
                return {
                    success: false,
                    type: 'analysis',
                    error: 'Backend server is not available. Please start the Flask backend first.',
                    prompt: userPrompt
                };
            }
            // Build context from files if provided (to match backend logic)
            let context = '';
            if (files && files.length > 0) {
                // Summarize file info for context (file name, type, size)
                const contextParts = [];
                for (const file of files) {
                    contextParts.push(`File: ${file.name || file.path || ''}`);
                    if (file.language)
                        contextParts.push(`Language: ${file.language}`);
                    if (file.type)
                        contextParts.push(`Type: ${file.type}`);
                    if (file.size)
                        contextParts.push(`Size: ${file.size}`);
                    contextParts.push('');
                }
                context = contextParts.join('\n');
            }
            else if (vsContext) {
                // analyzeContext is removed; just return empty string
            }
            // Use the intelligent endpoint
            const result = await this.backendClient.analyzeAndExecute(userPrompt, context, files);
            console.log(result);
            if (result.success) {
                vscode.window.showInformationMessage(`📝 Analysis completed successfully`);
            }
            return {
                ...result,
                files: result.files // propagate files
            };
        }
        catch (error) {
            vscode.window.showErrorMessage(`❌ Error: ${error}`);
            return {
                success: false,
                type: 'analysis',
                error: `Agent error: ${error}`,
                prompt: userPrompt
            };
        }
    }
}
exports.NLPAgent = NLPAgent;
//# sourceMappingURL=nlp-agent.js.map