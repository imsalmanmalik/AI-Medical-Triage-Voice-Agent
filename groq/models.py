from pydantic import BaseModel 
from typing import List


class FinalAns(BaseModel):
    patient_name: str
    doctor_name: str
    booking_number: int
    department_of_doctor: str
    symptoms: List[str]

class ChatSession:
    def __init__(self, sid):
        self.sid = sid
        self.messages = []

    def add_message(self, sender, message):
        self.messages.append({"sender": sender, "message": message})

    def get_history(self):
        return self.messages

    def reset_conversation(self):
        self.messages = []

class ChatRequest(BaseModel):
    callSID: str
    user_input: str

class HangupRequest(BaseModel):
    callSid: str