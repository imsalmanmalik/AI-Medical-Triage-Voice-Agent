import express, { Request, Response } from 'express';
import dotenv from 'dotenv';
import WebSocket, { Server as WebSocketServer } from 'ws';
import twilio from 'twilio';
import axios from 'axios';
import bodyParser from 'body-parser';
import cors from 'cors';

dotenv.config();

const SKYPE_NUMBER = process.env.SKYPE_NUMBER || "+18604694726";
const TWILIO_NUMBER = process.env.TWILIO_NUMBER as string;
const accountSid = process.env.TWILIO_ACCOUNT_SID as string;
const authToken = process.env.TWILIO_AUTH_TOKEN as string;
const baseUrl = process.env.BASE_URL as string;
const misteralUrl = process.env.MISTERAL_URL as string;

const twilioClient = twilio(accountSid, authToken);

const app = express();
const port = 3001;

app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());
app.use(cors());

const server = app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});

const wss = new WebSocketServer({ server });

// Extend WebSocket interface to include custom properties
interface CustomWebSocket extends WebSocket {
  callSid?: string; // Custom property to store callSid
  customUrl?: string; // Custom property to store WebSocket URL
}

interface ActiveConnections {
  [key: string]: CustomWebSocket;
}

interface ActiveCalls {
  [key: string]: boolean;
}

const activeConnections: ActiveConnections = {};
const activeCalls: ActiveCalls = {};

class ConnectionManager {
  private isTwilioSpeaking: { [key: string]: boolean } = {};

  async connect(ws: CustomWebSocket, callSid: string): Promise<void> {
    console.log("🚀 ~ ConnectionManager ~ connect ~ callSid:", callSid);
    ws.callSid = callSid;
    activeConnections[callSid] = ws;
    activeCalls[callSid] = true;
    this.isTwilioSpeaking[callSid] = true;

    ws.on('close', (code) => {
      console.log(`WebSocket closed for callSid: ${callSid} with code: ${code}`);
      if (code !== 1000 && ws.url) {
        setTimeout(() => this.reconnect(callSid, ws.url!), RECONNECT_INTERVAL);
      }
    });
  }

  async reconnect(callSid: string, wsUrl: string): Promise<void> {
    if (!activeCalls[callSid]) {
      console.log(`Call ${callSid} is no longer active. Not attempting to reconnect.`);
      return;
    }

    console.log(`Attempting to reconnect WebSocket for callSid: ${callSid}`);
    const newWs: CustomWebSocket = new WebSocket(wsUrl);

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

  disconnect(callSid: string): void {
    console.log("disconnecting...");
    delete activeConnections[callSid];
    delete this.isTwilioSpeaking[callSid];
    delete activeCalls[callSid];
    console.log("disconnected..!");
  }

  async getOpenAIResponse(text: string, callSid: string): Promise<string> {
    try {
      const response = await axios.post(`${misteralUrl}?user_input={text}&call_sid=${callSid}`);
      return response.data.text;
    } catch (error) {
      console.error("🚀 ~ ConnectionManager ~ getOpenAIResponse ~ error:", error);
      throw new Error("Error getting AI response");
    }
  }

  async playResponse(callSid: string, responseText: string): Promise<void> {
    try {
      const twiml = new twilio.twiml.VoiceResponse();
      twiml.say(responseText);
      twiml.pause({ length: 1 });

      const gather = twiml.gather({
        speechTimeout: "auto",
        input: ["speech"],
        action: `${baseUrl}/process_response?CallSid=${callSid}`,
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
    } catch (error) {
      console.error("🚀 ~ ConnectionManager ~ playResponse ~ error:", error);
      throw new Error("Error playing response");
    }
  }
}

const manager = new ConnectionManager();

const RECONNECT_INTERVAL = 5000; // 5 seconds

function reconnect(callSid: string, wsUrl: string): void {
  if (!activeCalls[callSid]) {
    console.log(`Call ${callSid} is no longer active. Not attempting to reconnect.`);
    return;
  }

  console.log(`Attempting to reconnect WebSocket for callSid: ${callSid}`);
  const newWs: CustomWebSocket = new WebSocket(wsUrl);

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

async function handleWebSocketMessage(ws: CustomWebSocket, message: WebSocket.Data): Promise<void> {
  try {
    const msg = JSON.parse(message.toString());
    const callSid = ws.callSid;

    switch (msg.event) {
      case 'connected':
        console.log('A new call has connected.');
        manager.connect(ws, callSid!);
        break;
      case 'start':
        console.log(`Starting Media Stream ${msg.streamSid}`);
        break;
      case 'media':
        // Handle media messages if needed
        break;
      case 'stop':
        console.log('Call Has Ended');
        manager.disconnect(callSid!);
        break;
    }
  } catch (error) {
    console.error('Error processing message:', error);
  }
}

app.post("/make_call", async (req: Request, res: Response) => {
  try {
    console.log("Initiating call...");
    const data = req.body;
    const skypeNumber = data.to || SKYPE_NUMBER;
    const seedPhrase = data.seedPhrase || "Hello, this is your voice assistant. How can I assist you?";
    const response = new twilio.twiml.VoiceResponse();
    const start = response.start();
    start.stream({
      name: "Example Audio Stream",
      url: `wss://${req.headers.host}/ws`,
    });
    const gather = response.gather({
      speechTimeout: "auto",
      input: ["speech"],
      action: `${baseUrl}/process_response`,
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
    wss.on("connection", (ws: CustomWebSocket) => {
      ws.callSid = call.sid;
      ws.customUrl = `wss://${req.headers.host}/ws`; // Store the WebSocket URL for reconnection
      console.log(`WebSocket connection established for callSid: ${call.sid}`);
      manager.connect(ws, call.sid);
    });
    
    res.json({ status: "success", call_sid: call.sid });

    
  } catch (error) {
    console.log(" ~ app.post ~ error:", error);
    res.status(500).json({ message: "Error initiating call", error });
  }
});

app.post("/process_response", async (req: Request, res: Response) => {
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
  } catch (error) {
    console.error("Error processing response:", error);
    const errorMessage = "Sorry, I encountered an error. Please try again later.";
    await manager.playResponse(callSid, errorMessage);
    return res.status(500).json({ message: "Error processing response", error });
  }
});

app.post("/hangup", (req: Request, res: Response) => {
  const callSid = req.body.callSid;
  console.log(`Hangup request received for callSid: ${callSid}`);
  manager.disconnect(callSid); // Properly disconnect the call
  res.sendStatus(200);
});

app.post("/incoming_call", async (req: Request, res: Response) => {
  try {
    const callSid = req.body.CallSid;
    const fromNumber = req.body.From;
    console.log(`Incoming call from ${fromNumber} with CallSid: ${callSid}`);

    // Generate the TwiML response for the incoming call
    const response = new twilio.twiml.VoiceResponse();
    const start = response.start();
    start.stream({
      name: "Example Audio Stream",
      url: `wss://${req.headers.host}/ws`,
    });
    const gather = response.gather({
      speechTimeout: "auto",
      input: ["speech"],
      action: `${baseUrl}/process_response`,
      speechModel: "phone_call",
    });
    gather.say("Hello, this is your voice assistant. How can I assist you?");

    activeCalls[callSid] = true; // Mark the call as active
    res.type('text/xml').send(response.toString());

    wss.on("connection", (ws: CustomWebSocket) => {
      ws.callSid = callSid;
      ws.customUrl = `wss://${req.headers.host}/ws`; // Store the WebSocket URL for reconnection
      console.log(`WebSocket connection established for incoming callSid: ${callSid}`);
      manager.connect(ws, callSid);
    });
  } catch (error) {
    console.log("Error handling incoming call:", error);
    res.status(500).json({ message: "Error handling incoming call", error });
  }
});

wss.on("connection", function connection(ws: CustomWebSocket) {
  console.log("New Connection Initiated");

  const interval = setInterval(function ping() {
    if (ws.readyState === WebSocket.OPEN) {
      ws.ping();
    } else {
      clearInterval(interval);
    }
  }, 30_000);

  ws.on("pong", () => {
    console.log("Pong received");
  });

  ws.on("message", async function incoming(message: WebSocket.Data) {
    await handleWebSocketMessage(ws, message);
  });

  ws.on("close", (code: number, reason: string) => {
    if (code === 1005) {
      console.log("No status code provided. Attempting to reconnect...");
      setTimeout(() => reconnect(ws.callSid!, ws.url!), RECONNECT_INTERVAL);
    }
    console.log("WebSocket connection closed with code:", code, reason);
  });
});