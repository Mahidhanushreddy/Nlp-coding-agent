import { BackendClient } from './backend-client';
import type { AgentConfig, VSCodeContext } from './types';
import * as vscode from 'vscode';
import * as path from 'path';

export class NLPAgent {
  private backendClient: BackendClient;
  private config: AgentConfig;
  private context: vscode.ExtensionContext;

  constructor(context: vscode.ExtensionContext, config: AgentConfig) {
    this.context = context;
    this.config = config;
    
    // Use backend URL if provided, otherwise default to localhost:5000
    const backendUrl = config.backendUrl || 'http://localhost:5000';
    this.backendClient = new BackendClient({
      backendUrl: backendUrl,
      timeout: config.timeout
    });
  }

  async analyzeAndExecute(userPrompt: string, vsContext?: VSCodeContext, files?: any[]): Promise<{ 
    success: boolean; 
    type: 'analysis'; 
    output?: string; 
    sections?: any;
    error?: string; 
    prompt: string,
    files?: any[]
  }> {
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
        const contextParts: string[] = [];
        for (const file of files) {
          contextParts.push(`File: ${file.name || file.path || ''}`);
          if (file.language) contextParts.push(`Language: ${file.language}`);
          if (file.type) contextParts.push(`Type: ${file.type}`);
          if (file.size) contextParts.push(`Size: ${file.size}`);
          contextParts.push('');
        }
        context = contextParts.join('\n');
      } else if (vsContext) {
        // analyzeContext is removed; just return empty string
      }
      
      // Use the intelligent endpoint
      const result = await this.backendClient.analyzeAndExecute(userPrompt, context, files);
      console.log(result)
      
      if (result.success) {
        vscode.window.showInformationMessage(`📝 Analysis completed successfully`);
      }
      
      return {
        ...result,
        files: result.files // propagate files
      };
    } catch (error) {
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