import { Schema, model, Document } from 'mongoose';

interface IAgent extends Document {
  name: string;
  instructions?: string;
  greetingPhrase?: string;
  type: 'Inbound' | 'Outbound';
  isActive: boolean;
  createdAt: Date;
}

const AgentSchema = new Schema<IAgent>({
  name: { type: String, required: true },
  instructions: { type: String },
  greetingPhrase: { type: String },
  type: { type: String, enum: ['Inbound', 'Outbound'], required: true },
  isActive: { type: Boolean, default: true },
  createdAt: { type: Date, default: Date.now },
});

export const Agent = model<IAgent>('Agent', AgentSchema);