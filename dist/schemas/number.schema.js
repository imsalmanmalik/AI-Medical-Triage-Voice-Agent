"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Number = void 0;
const mongoose_1 = require("mongoose");
const NumberSchema = new mongoose_1.Schema({
    phoneNumber: { type: String, required: true, unique: true },
    createdAt: { type: Date, default: Date.now },
    isActive: { type: Boolean, default: true },
    agent: { type: mongoose_1.Schema.Types.ObjectId, ref: 'Agent' },
});
exports.Number = (0, mongoose_1.model)('Number', NumberSchema);
