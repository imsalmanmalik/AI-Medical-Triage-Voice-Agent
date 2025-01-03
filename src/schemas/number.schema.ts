import { Schema, model, Document } from 'mongoose';

interface INumber extends Document {
  phoneNumber: string;
  createdAt: Date;
  isActive: boolean;
  agent: Schema.Types.ObjectId;
}

const NumberSchema = new Schema<INumber>({
  phoneNumber: { type: String, required: true, unique: true },
  createdAt: { type: Date, default: Date.now },
  isActive: { type: Boolean, default: true },
  agent: { type: Schema.Types.ObjectId, ref: 'Agent' },
});

export const Number = model<INumber>('Number', NumberSchema);