import * as vscode from 'vscode';

export interface ModelResponse {
  generated_text: string;
  confidence?: number;
}

export interface AgentConfig {
  modelApiUrl: string;
  apiKey?: string;
  maxRetries: number;
  timeout: number;
  model?: string;
  backendUrl?: string;
}

export interface VSCodeContext {
  workspaceRoot: string;
  activeEditor?: vscode.TextEditor;
  selectedText?: string;
  currentFile?: string;
  language?: string;
}

export interface ResponseSections {
  analysis: string;
  packages: string[];
  solution: string;
  run_commands: string[];
  usage: string;
}

export interface AnalysisResponse {
  success: boolean;
  type: 'analysis';
  output?: string;
  sections?: ResponseSections;
  error?: string;
  prompt: string;
} 