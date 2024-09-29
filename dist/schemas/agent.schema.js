"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Agent = void 0;
const mongoose_1 = require("mongoose");
const AgentSchema = new mongoose_1.Schema({
    name: { type: String, required: true },
    instructions: { type: String },
    greetingPhrase: { type: String },
    type: { type: String, enum: ['Inbound', 'Outbound'], required: true },
    isActive: { type: Boolean, default: true },
    createdAt: { type: Date, default: Date.now },
});
exports.Agent = (0, mongoose_1.model)('Agent', AgentSchema);
