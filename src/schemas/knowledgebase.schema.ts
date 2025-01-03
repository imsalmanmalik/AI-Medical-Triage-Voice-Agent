import { Schema, model, Document } from 'mongoose';

interface IKnowledgeBase extends Document {
  agent: Schema.Types.ObjectId;
  type: 'Web' | 'Document' | 'Text';
  content: string;
  metaData?: Record<string, any>;
  createdAt: Date;
  isActive: boolean;
}

const KnowledgeBaseSchema = new Schema<IKnowledgeBase>({
  agent: { type: Schema.Types.ObjectId, ref: 'Agent', required: true },
  type: { type: String, enum: ['Web', 'Document', 'Text'], required: true },
  content: { type: String, required: true },
  metaData: { type: Object },
  createdAt: { type: Date, default: Date.now },
  isActive: { type: Boolean, default: true },
});

export const KnowledgeBase = model<IKnowledgeBase>('KnowledgeBase', KnowledgeBaseSchema);