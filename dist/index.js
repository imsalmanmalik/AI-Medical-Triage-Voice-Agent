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
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const dotenv_1 = __importDefault(require("dotenv"));
const ws_1 = __importStar(require("ws"));
const twilio_1 = __importDefault(require("twilio"));
const axios_1 = __importDefault(require("axios"));
const body_parser_1 = __importDefault(require("body-parser"));
const cors_1 = __importDefault(require("cors"));
dotenv_1.default.config();
const SKYPE_NUMBER = process.env.SKYPE_NUMBER || "+18304762217";
const TWILIO_NUMBER = process.env.TWILIO_NUMBER;
const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;
const twilioClient = (0, twilio_1.default)(accountSid, authToken);
const app = (0, express_1.default)();
const port = 3001;
app.use(body_parser_1.default.urlencoded({ extended: true }));
app.use(body_parser_1.default.json());
app.use((0, cors_1.default)());
const server = app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});
const wss = new ws_1.Server({ server });
const activeConnections = {};
const activeCalls = {};
class ConnectionManager {
    isTwilioSpeaking = {};
    async connect(ws, callSid) {
        console.log("🚀 ~ ConnectionManager ~ connect ~ callSid:", callSid);
        ws.callSid = callSid;
        activeConnections[callSid] = ws;
        activeCalls[callSid] = true;
        this.isTwilioSpeaking[callSid] = true;
        ws.on('close', (code) => {
            console.log(`WebSocket closed for callSid: ${callSid} with code: ${code}`);
            if (code !== 1000 && ws.url) {
                setTimeout(() => this.reconnect(callSid, ws.url), RECONNECT_INTERVAL);
            }
        });
    }
    async reconnect(callSid, wsUrl) {
        if (!activeCalls[callSid]) {
            console.log(`Call ${callSid} is no longer active. Not attempting to reconnect.`);
            return;
        }
        console.log(`Attempting to reconnect WebSocket for callSid: ${callSid}`);
        const newWs = new ws_1.default(wsUrl);
        newWs.on('open', () => {
            console.log(`Reconnected WebSocket for callSid: ${callSid}`);
            activeConnections[callSid] = newWs;
            this.connect(newWs, callSid);
        });
        newWs.on('message', async (message) => {
            await handleWebSocketMessage(newWs, message);
        });
        newWs.on('close', (code) => {
            console.log(`WebSocket closed again for callSid: ${callSid} with code: ${code}`);
            if (code !== 1000 && activeCalls[callSid]) {
                setTimeout(() => this.reconnect(callSid, wsUrl), RECONNECT_INTERVAL);
            }
        });
        newWs.on('error', (error) => {
            console.error(`WebSocket error for callSid: ${callSid}`, error);
            newWs.close();
        });
    }
    disconnect(callSid) {
        console.log("disconnecting...");
        delete activeConnections[callSid];
        delete this.isTwilioSpeaking[callSid];
        delete activeCalls[callSid];
        console.log("disconnected..!");
    }
    async getOpenAIResponse(text, callSid) {
        try {
            const response = await axios_1.default.post(`http://44.211.2.31:3000/chat`, {
                user_input: text,
                call_sid: callSid,
            });
            return response.data.text;
        }
        catch (error) {
            console.error("🚀 ~ ConnectionManager ~ getOpenAIResponse ~ error:", error);
            throw new Error("Error getting AI response");
        }
    }
    async playResponse(callSid, responseText) {
        try {
            const twiml = new twilio_1.default.twiml.VoiceResponse();
            twiml.say(responseText);
            twiml.pause({ length: 1 });
            const gather = twiml.gather({
                speechTimeout: "auto",
                input: ["speech"],
                action: `https://voiceai.layerthreesolutions.com/process_response?CallSid=${callSid}`,
                speechModel: "phone_call",
                finishOnKey: "none",
            });
            gather.say("Please respond now.");
            const twimlString = twiml.toString();
            console.log(`Sending TwiML response to Twilio for callSid: ${callSid}`);
            await twilioClient.calls(callSid).update({ twiml: twimlString });
            this.isTwilioSpeaking[callSid] = true;
            setTimeout(() => {
                this.isTwilioSpeaking[callSid] = false;
            }, 1000);
        }
        catch (error) {
            console.error("🚀 ~ ConnectionManager ~ playResponse ~ error:", error);
            throw new Error("Error playing response");
        }
    }
}
const manager = new ConnectionManager();
const RECONNECT_INTERVAL = 5000; // 5 seconds
function reconnect(callSid, wsUrl) {
    if (!activeCalls[callSid]) {
        console.log(`Call ${callSid} is no longer active. Not attempting to reconnect.`);
        return;
    }
    console.log(`Attempting to reconnect WebSocket for callSid: ${callSid}`);
    const newWs = new ws_1.default(wsUrl);
    newWs.on('open', () => {
        console.log(`Reconnected WebSocket for callSid: ${callSid}`);
        activeConnections[callSid] = newWs;
        manager.connect(newWs, callSid);
    });
    newWs.on('message', async (message) => {
        await handleWebSocketMessage(newWs, message);
    });
    newWs.on('close', (code) => {
        console.log(`WebSocket closed again for callSid: ${callSid} with code: ${code}`);
        if (code !== 1000 && activeCalls[callSid]) {
            setTimeout(() => reconnect(callSid, wsUrl), RECONNECT_INTERVAL);
        }
    });
    newWs.on('error', (error) => {
        console.error(`WebSocket error for callSid: ${callSid}`, error);
        newWs.close();
    });
}
async function handleWebSocketMessage(ws, message) {
    try {
        const msg = JSON.parse(message.toString());
        const callSid = ws.callSid;
        switch (msg.event) {
            case 'connected':
                console.log('A new call has connected.');
                manager.connect(ws, callSid);
                break;
            case 'start':
                console.log(`Starting Media Stream ${msg.streamSid}`);
                break;
            case 'media':
                // Handle media messages if needed
                break;
            case 'stop':
                console.log('Call Has Ended');
                manager.disconnect(callSid);
                break;
        }
    }
    catch (error) {
        console.error('Error processing message:', error);
    }
}
app.post("/make_call", async (req, res) => {
    try {
        console.log("Initiating call...");
        const data = req.body;
        const skypeNumber = data.to || SKYPE_NUMBER;
        const seedPhrase = data.seedPhrase || "Hello, this is your voice assistant. How can I assist you?";
        const response = new twilio_1.default.twiml.VoiceResponse();
        const start = response.start();
        start.stream({
            name: "Example Audio Stream",
            url: `wss://${req.headers.host}/ws`,
        });
        const gather = response.gather({
            speechTimeout: "auto",
            input: ["speech"],
            action: `https://voiceai.layerthreesolutions.com/process_response`,
            speechModel: "phone_call",
        });
        gather.say(seedPhrase);
        const call = await twilioClient.calls.create({
            twiml: response.toString(),
            to: skypeNumber,
            from: TWILIO_NUMBER,
            record: true,
        });
        console.log(`Call SID: ${call.sid}`);
        activeCalls[call.sid] = true; // Mark the call as active
        res.json({ status: "success", call_sid: call.sid });
        wss.on("connection", (ws) => {
            ws.callSid = call.sid;
            ws.customUrl = `wss://${req.headers.host}/ws`; // Store the WebSocket URL for reconnection
            console.log(`WebSocket connection established for callSid: ${call.sid}`);
            manager.connect(ws, call.sid);
        });
    }
    catch (error) {
        console.log(" ~ app.post ~ error:", error);
        res.status(500).json({ message: "Error initiating call", error });
    }
});
app.post("/process_response", async (req, res) => {
    const callSid = req.body.CallSid;
    const responseText = req.body.SpeechResult;
    if (!responseText) {
        console.log("No speech result received. Repeating previous AI response.");
        return res.sendStatus(200); // Ensure this does not prematurely end the call
    }
    try {
        console.log("Processing your request...");
        const aiResponse = await manager.getOpenAIResponse(responseText, callSid);
        console.log("AI Response:", aiResponse);
        if (aiResponse) {
            await manager.playResponse(callSid, aiResponse);
            return res.sendStatus(200); // Delay the sendStatus to ensure playResponse completes
        }
        throw new Error("Failed to get AI response.");
    }
    catch (error) {
        console.error("Error processing response:", error);
        const errorMessage = "Sorry, I encountered an error. Please try again later.";
        await manager.playResponse(callSid, errorMessage);
        return res.status(500).json({ message: "Error processing response", error });
    }
});
app.post("/hangup", (req, res) => {
    const callSid = req.body.callSid;
    console.log(`Hangup request received for callSid: ${callSid}`);
    manager.disconnect(callSid); // Properly disconnect the call
    res.sendStatus(200);
});
app.post("/incoming_call", async (req, res) => {
    try {
        const callSid = req.body.CallSid;
        const fromNumber = req.body.From;
        console.log(`Incoming call from ${fromNumber} with CallSid: ${callSid}`);
        // Generate the TwiML response for the incoming call
        const response = new twilio_1.default.twiml.VoiceResponse();
        const start = response.start();
        start.stream({
            name: "Example Audio Stream",
            url: `wss://${req.headers.host}/ws`,
        });
        const gather = response.gather({
            speechTimeout: "auto",
            input: ["speech"],
            action: `https://voiceai.layerthreesolutions.com/process_response`,
            speechModel: "phone_call",
        });
        gather.say("Hello, this is your voice assistant. How can I assist you?");
        activeCalls[callSid] = true; // Mark the call as active
        res.type('text/xml').send(response.toString());
        wss.on("connection", (ws) => {
            ws.callSid = callSid;
            ws.customUrl = `wss://${req.headers.host}/ws`; // Store the WebSocket URL for reconnection
            console.log(`WebSocket connection established for incoming callSid: ${callSid}`);
            manager.connect(ws, callSid);
        });
    }
    catch (error) {
        console.log("Error handling incoming call:", error);
        res.status(500).json({ message: "Error handling incoming call", error });
    }
});
wss.on("connection", function connection(ws) {
    console.log("New Connection Initiated");
    const interval = setInterval(function ping() {
        if (ws.readyState === ws_1.default.OPEN) {
            ws.ping();
        }
        else {
            clearInterval(interval);
        }
    }, 30_000);
    ws.on("pong", () => {
        console.log("Pong received");
    });
    ws.on("message", async function incoming(message) {
        await handleWebSocketMessage(ws, message);
    });
    ws.on("close", (code, reason) => {
        if (code === 1005) {
            console.log("No status code provided. Attempting to reconnect...");
            setTimeout(() => reconnect(ws.callSid, ws.url), RECONNECT_INTERVAL);
        }
        console.log("WebSocket connection closed with code:", code, reason);
    });
});
