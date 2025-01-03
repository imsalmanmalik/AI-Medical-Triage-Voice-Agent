import { Schema, model, Document } from 'mongoose';

interface ICall extends Document {
  agent: Schema.Types.ObjectId;
  numberTo?: Schema.Types.ObjectId;
  numberFrom?: Schema.Types.ObjectId;
  contactTo?: Schema.Types.ObjectId;
  contactFrom?: Schema.Types.ObjectId;
  createdAt: Date;
  duration?: number;
  recordingUrl?: string;
  transcription?: string;
  summary?: string;
}

const CallSchema = new Schema<ICall>({
  agent: { type: Schema.Types.ObjectId, ref: 'Agent', required: true },
  numberTo: { type: Schema.Types.ObjectId, ref: 'Number' },
  numberFrom: { type: Schema.Types.ObjectId, ref: 'Number' },
  contactTo: { type: Schema.Types.ObjectId, ref: 'Contact' },
  contactFrom: { type: Schema.Types.ObjectId, ref: 'Contact' },
  createdAt: { type: Date, default: Date.now },
  duration: { type: Number },
  recordingUrl: { type: String },
  transcription: { type: String },
  summary: { type: String },
});

export const Call = model<ICall>('Call', CallSchema);