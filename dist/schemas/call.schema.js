"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Call = void 0;
const mongoose_1 = require("mongoose");
const CallSchema = new mongoose_1.Schema({
    agent: { type: mongoose_1.Schema.Types.ObjectId, ref: 'Agent', required: true },
    numberTo: { type: mongoose_1.Schema.Types.ObjectId, ref: 'Number' },
    numberFrom: { type: mongoose_1.Schema.Types.ObjectId, ref: 'Number' },
    contactTo: { type: mongoose_1.Schema.Types.ObjectId, ref: 'Contact' },
    contactFrom: { type: mongoose_1.Schema.Types.ObjectId, ref: 'Contact' },
    createdAt: { type: Date, default: Date.now },
    duration: { type: Number },
    recordingUrl: { type: String },
    transcription: { type: String },
    summary: { type: String },
});
exports.Call = (0, mongoose_1.model)('Call', CallSchema);
