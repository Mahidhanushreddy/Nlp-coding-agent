import axios from 'axios';
import * as vscode from 'vscode';

export interface BackendConfig {
  backendUrl: string;
  timeout: number;
}

export interface ResponseSections {
  analysis: string;
  packages: string[];
  solution: string;
  run_commands: string[];
  usage: string;
}

export interface FileInfo {
  path: string;
  language: string;
}

export interface ContextAnalysis {
  success: boolean;
  context?: string;
  analysis?: any[];
  error?: string;
}

export class BackendClient {
  private config: BackendConfig;

  constructor(config: BackendConfig) {
    this.config = config;
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await axios.get(`${this.config.backendUrl}/api/health`, {
        timeout: 5000
      });
      return response.status === 200;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }

  async analyzeAndExecute(prompt: string, context?: string, files?: any[]): Promise<{ 
    success: boolean; 
    type: 'analysis'; 
    output?: string; 
    sections?: ResponseSections;
    error?: string; 
    prompt: string,
    files?: any[]
  }> {
    try {
      const requestBody: any = { prompt };
      if (context) {
        requestBody.context = context;
      }
      if (files && files.length > 0) {
        requestBody.files = files;
      }

      const response = await fetch(`${this.config.backendUrl}/api/analyze-and-execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
        signal: AbortSignal.timeout(this.config.timeout)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json() as any;
      return {
        success: data.success,
        type: data.type,
        output: data.output,
        sections: data.sections,
        error: data.error,
        prompt: data.prompt,
        files: data.files
      };
    } catch (error) {
      console.error('Error in analyzeAndExecute:', error);
      return {
        success: false,
        type: 'analysis',
        error: `Backend error: ${error}`,
        prompt: prompt
      };
    }
  }
} 