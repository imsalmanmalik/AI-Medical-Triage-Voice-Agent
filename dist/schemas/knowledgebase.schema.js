"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.KnowledgeBase = void 0;
const mongoose_1 = require("mongoose");
const KnowledgeBaseSchema = new mongoose_1.Schema({
    agent: { type: mongoose_1.Schema.Types.ObjectId, ref: 'Agent', required: true },
    type: { type: String, enum: ['Web', 'Document', 'Text'], required: true },
    content: { type: String, required: true },
    metaData: { type: Object },
    createdAt: { type: Date, default: Date.now },
    isActive: { type: Boolean, default: true },
});
exports.KnowledgeBase = (0, mongoose_1.model)('KnowledgeBase', KnowledgeBaseSchema);
