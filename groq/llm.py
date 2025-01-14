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

bot = ReminderBot(system_prompt)
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
def chat(request: ChatRequest):
    try:
        # Validate request
        if not request.call_sid or not request.user_input:
            raise HTTPException(status_code=400, detail="Missing call_sid or user_input")

        # Extract input and call session ID
        user_input = request.user_input
        call_sid = request.call_sid
        print("User:", user_input)

        # Get or create a chat session for the current call
        chat_session = get_or_create_chat_session(call_sid)
        chat_session.add_message("user", user_input)

        # Handle "bye" case directly
        if "bye" in user_input.lower():
            bot.add_message_to_session(call_sid, "assistant", "Goodbye!")
            bot.reset_conversation(call_sid)
            return {"response": "Goodbye!"}

        # Generate response from the bot
        response = bot.generate_response(call_sid, user_input)
        print("Bot Response:", response)

        # Handle symptom-related responses
        if isinstance(response, dict) and "symptom" in response:
            questions = get_possible_questions(response["symptom"])
            print("Possible Questions:", questions)

            if questions and isinstance(questions, list):
                question = questions[0]
                bot.add_message_to_session(call_sid, "assistant", question)
                return {"response": question}

            elif isinstance(questions, str):
                response_message = "Ok, any other symptoms that you are facing?"
                bot.add_message_to_session(call_sid, "assistant", response_message)
                return {"response": response_message}

        # Handle specialty-related responses
        if isinstance(response, dict) and "specialty" in response:
            doctor_data = get_doctors_by_expertise(response["specialty"])
            print("Doctor Data:", doctor_data)

            if not doctor_data:
                no_doctor_message = (
                    "Your symptoms look like a {response['specialty']} could help you out. "
                    "I'm sorry, we don't have any doctors for this specialty. Bye."
                )
                bot.add_message_to_session(call_sid, "assistant", no_doctor_message)
                return {"response": no_doctor_message}

            message = (
                f"For your symptoms, I recommend Doctor {doctor_data[0]['name']} who is a {doctor_data[0]['expertise']}. "
                "Would you like to book an appointment?"
            )
            bot.add_message_to_session(call_sid, "assistant", message)
            bot.add_message_to_session(call_sid, "assistant", str(doctor_data))
            return {"response": message}

        # Handle patient name and booking-related responses
        if (
            isinstance(response, dict)
            and "patient_name" in response
            and "doctor_name" in response
        ):
            final_ans = FinalAns(**response)
            booking_id = process_patient_booking(final_ans, call_sid)

            if booking_id:
                success_message = f"Booking created successfully. Booking ID: {booking_id}"
                bot.add_message_to_session(call_sid, "assistant", success_message)
                return {"response": success_message}

        # General fallback response
        return {"response": response}

    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        bot.add_message_to_session(call_sid, "assistant", error_message)
        return {"response": error_message}




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

