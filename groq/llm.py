from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv, find_dotenv
from models import FinalAns, ChatSession, ChatRequest, HangupRequest
from threading import Lock
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from pydantic import BaseModel
import json

from service import *
from services import *
from models import *

bot = ReminderBot()
class UserInput(BaseModel):
    prompt: str

text_history = "" #convert to a data structure
chat_sessions = {}
lock = Lock()

final_ans = ""

processed_symptoms = set() #so tool call isn't made for the same symptom again

def get_related_questions_tool(user_input, symp):

    print("Tool is being called with user input:", user_input)

    # Process the symptom matching
    symptom_choices = [symptom['symptom'] for symptom in symp_data]
    best_match = process.extractOne(user_input, symptom_choices, scorer=fuzz.partial_ratio)

    if best_match in processed_symptoms:
        print(f"Symptom '{user_input}' has already been processed. Skipping tool call.")
        return []

    processed_symptoms.add(best_match)

    if best_match:
        matched_symptom = best_match[0]
        for symptom in symp_data:
            if symptom['symptom'] == matched_symptom:
                return symptom['possible_questions']
    return ["No matching symptoms found. Please provide more details."]

tool_questions = []
asked_questions = set() 

app = FastAPI()
@app.post("/chat")
def chat(user_input: UserInput):
    try:
        user_prompt = user_input.prompt
        
        response = bot.generate_response(user_prompt)

        if isinstance(response, dict) and 'symptom' in response:
            questions = get_possible_questions(response['symptom'])
            if questions:
                bot.add_message("assistant", questions[0])
                return {"response": questions[0]}

        if isinstance(response, dict) and 'specialty' in response:
            print (response)
            doctor_data = get_doctors_by_expertise(response['specialty'])
            print (doctor_data)

            message = "For your symptoms, I recommend Doctor " + doctor_data[0]['name'] + " who is a " + doctor_data[0]['expertise'] + ", Would you like to book an appointment?"
            bot.add_message("assistant", message)
            bot.add_message("assistant", str(doctor_data))
            return {"response": message}

        if isinstance(response, dict) and 'patient_name' in response: 
            final_ans = FinalAns(**response)
            booking_id = process_patient_booking(final_ans)
            if booking_id:
                bot.add_message("assistant", f"Booking created successfully. Booking ID: {booking_id}")
                return {"response": f"Booking created successfully. Booking ID: {booking_id}"}

        # if 'bye' in response.choices[0].message.content.lower():
        #     bot.add_message("assistant", "Goodbye!")
        #     bot.reset_conversation()
        #     return {"response": "Goodbye!"}
        
        return {"response": response.choices[0].message.content}
    
    except Exception as e:
        return {"response": f"An error occurred: {str(e)}"}

async def hangup(request: HangupRequest):
    call_sid = request.callSid  # Get the callSID from the request
    print(f"Hangup request received for callSid: {call_sid}")

    # Retrieve the chat session using the callSid
    chat_session = get_or_create_chat_session(call_sid)  

    if chat_session:
        # Store the chat history before hanging up
        store_chat_history(call_sid, chat_session.get_history())

        # Reset or save the conversation as needed
        chat_session.reset_conversation()

    return {"message": "Call ended and chat history saved."}

