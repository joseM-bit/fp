import { BedrockClient, ListFoundationModelsCommand } from "@aws-sdk/client-bedrock";
import { BedrockRuntimeClient, ConverseCommand } from "@aws-sdk/client-bedrock-runtime";
import { BedrockAgentRuntimeClient, InvokeAgentCommand } from "@aws-sdk/client-bedrock-agent-runtime";
import { fromIni } from "@aws-sdk/credential-providers";
import dotenv from 'dotenv';


dotenv.config();

// Configuració
const REGION = process.env.AWS_REGION;
const credentials = fromIni({ profile: process.env.AWS_PROFILE });

const bedrock = new BedrockClient({ region: REGION, credentials });
const runtime = new BedrockRuntimeClient({ region: REGION, credentials });
const agentRuntime = new BedrockAgentRuntimeClient({ region: REGION, credentials });

export const getModels = async (req, res) => {
    try {
        const command = new ListFoundationModelsCommand({});
        const response = await bedrock.send(command);
        res.json({
            count: response.modelSummaries.length,
            models: response.modelSummaries.map(m => m.modelId)
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};

export const invokeNova = async (req, res) => {
    const { userInput, history = [] } = req.body;
    try {
        const command = new ConverseCommand({
            modelId: process.env.MODEL_ID,
            messages: [...history, { role: "user", content: [{ text: userInput }] }],
            inferenceConfig: { maxTokens: 400, temperature: 0.7 }
        });
        const response = await runtime.send(command);
        res.json({ text: response.output.message.content[0].text });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};

export const invokeAgent = async (req, res) => {
    const { userInput, sessionId } = req.body;
    try {
        const command = new InvokeAgentCommand({
            agentId: process.env.AGENT_ID,
            agentAliasId: process.env.AGENT_ALIAS_ID,
            sessionId: sessionId || `session-${Date.now()}`,
            inputText: userInput,
        });

        const response = await agentRuntime.send(command);
        let completion = "";
        for await (const event of response.completion) {
            if (event.chunk) {
                completion += Buffer.from(event.chunk.bytes).toString("utf-8");
            }
        }
        res.json({ response: completion });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
};