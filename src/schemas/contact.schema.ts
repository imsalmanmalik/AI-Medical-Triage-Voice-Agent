import { Schema, model, Document } from 'mongoose';

interface IContact extends Document {
  name: string;
  phoneNumber: string;
  email?: string;
  isActive: boolean;
  createdAt: Date;
}

const ContactSchema = new Schema<IContact>({
  name: { type: String, required: true },
  phoneNumber: { type: String, required: true, unique: true },
  email: { type: String, unique: true },
  isActive: { type: Boolean, default: true },
  createdAt: { type: Date, default: Date.now },
});

export const Contact = model<IContact>('Contact', ContactSchema);