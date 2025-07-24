"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.BackendClient = void 0;
const axios_1 = __importDefault(require("axios"));
class BackendClient {
    constructor(config) {
        this.config = config;
    }
    async healthCheck() {
        try {
            const response = await axios_1.default.get(`${this.config.backendUrl}/api/health`, {
                timeout: 5000
            });
            return response.status === 200;
        }
        catch (error) {
            console.error('Health check failed:', error);
            return false;
        }
    }
    async analyzeAndExecute(prompt, context, files) {
        try {
            const requestBody = { prompt };
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
            const data = await response.json();
            return {
                success: data.success,
                type: data.type,
                output: data.output,
                sections: data.sections,
                error: data.error,
                prompt: data.prompt,
                files: data.files
            };
        }
        catch (error) {
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
exports.BackendClient = BackendClient;
//# sourceMappingURL=backend-client.js.map