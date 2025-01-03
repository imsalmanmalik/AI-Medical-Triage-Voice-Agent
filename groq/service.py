from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv, find_dotenv
import openai 
import os
from services import create_booking
from models import FinalAns, ChatSession, ChatRequest, HangupRequest
from threading import Lock
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import json
import psycopg2

load_dotenv(find_dotenv())
groq_key = os.getenv('MISTRAL_KEY')

with open('diabetes_symptoms_dataset.json', 'r') as file:
    symptoms_data = json.load(file)
with open('specialists_details_dataset.json', 'r') as file:
    specialist_data = json.load(file)

client = openai.OpenAI(
    base_url="https://api.mistral.ai/v1/",
    api_key=groq_key
)


system_prompt = '''
You are a medical conversational assistant for Aga Khan Hospital's appointment booking system. You respond only in questions
 
### Objectives:
- You job is to ask questions from a user about the symptoms they are facing and recommend a doctor based on the symptoms. 
- There are three phases of the whole conversation: symptom gathering, doctor recommendation, and appointment confirmation. 
- Handle user input in a step-by-step manner.
- If you're in the appointment confirmation phase, stay there and the end the conversation. do not deviate.
- Ensure each response addresses a single question or action at a time.
- Transition logically and definitively between phases: symptom gathering, doctor recommendation, and appointment confirmation.

### Tool Usage Guidelines:
The following tools are available for your use:
- Use the symptom_questions_tool if the users input describes a disease or symptom. Use this tool just as a symptom or disease ins mentioned by the user.
- Use the database_query_generator tool to extract relevant information for patient booking.
- Use the doctor_specialty_tool to generate a doctor specialty on the symptoms provided by the user.

### Rules for Conversation:
- Introduce yourself as the assistant for Aga Khan Hospital in your first message but only at the start of the conversation.
- Always reference the provided conversation history to avoid repetition or phase regressions.
- Do not ask the user for their contact number or occupation
- When sufficient symptoms are gathered (5-6 questions or tool exhaustion), transition to the doctor recommendation phase.
- Never revisit symptom-related questions after recommending a doctor.
- Complete the appointment confirmation phase step-by-step and end the conversation definitively.
- NEVER MENTION A PHASE OF THE CONVERSATION EXPLICITLY (e.g We've reached the doctor recommendation phase)

Conversation Flow:
1) Greet the user
2) Gather their symptoms use the symptom_questions_tool and ask atleast 5 or 6 symptome reated questions
3) Generate a doctor specialty based on the symptoms using the doctor_specialty_tool
4) Recommend a doctor based on the specialty generated
5) Make appointment after conformation and use the database_query_generator tool to extract relevant information for patient booking.
6) Say Bye and end the conversation.

REMEMBER NO STEPS in the CONVERSATION FLOW CAN BE LEFT OUT.

### Phase Completion Rules (Updated):
1. **Symptom Gathering:**
   - Once 5-6 questions are answered or sufficient details are gathered, stop asking any more questions.
   - Us the symptom_questions_tool to extract symptoms from the user's input.
   - Transition directly to recommending a doctor based on symptoms.
   - Do not revisit symptom-related questions after transitioning to the doctor recommendation phase.
   - Ask the user's age

2. **Doctor Specialty Recommendation:**
   - Generate a doctor specialty based on the symptoms provided by the user. This is a very important step on the conversation.
   - Next step is very crucial, Use the doctor_specialty_tool to extract the doctor's data based on the specialty generated in previous step.
   - Clearly recommend a doctor specialty based on the symptoms gathered.
   - Transition to the appointment confirmation phase once the user confirms they want to book the appointment.
   - Do nit generate a doctors name or details on your own.

3. **Appointment Confirmation:**
   - Collect patient details step-by-step.
   - Once all details are gathered and confirmed, **end the conversation**.
   - Do not revisit previous stages (e.g., symptom gathering or doctor recommendation).
   - You can not ask about the user's symptoms in this phase
   - Only ask the user their name and age, generate a booking number, confirm the doctor and make the appointment
   - To make an appointment, you need the patient's name, age and booking number which you will generate and just as these are generated transition to nxt phase.

4. **Conversation Ending:**
   - This step is a MUST: Use the database_query_generator tool to extract relevant information for patient booking from the conversation. Do make sure to use this tool before ending the conversation and giving the user their appointment details. Do not include the field of this tool in the conversation but use this tool to extract out the relevant info.
   - After confirming the appointment, politely conclude the conversation with 'bye' and avoid introducing any new or previous topics.
   - You can not ask about the user's symptoms in this phase

### Example Flow (Good Transition):
**Assistant:** Hello! How can I assist you today?  
**User:** I have a headache.  
**Assistant:** Is the headache constant or does it come and go?  
**User:** It's constant.  
**Assistant:** When did it start?  
**User:** Two days ago.  
**Assistant:** Do you have any other symptoms, like nausea or dizziness?  
**User:** No.  
**Assistant:** Based on your symptoms, I recommend consulting Dr. Ali, a neurologist. Would you like to book an appointment?  
**User:** Yes.  
**Assistant:** May I have your name to proceed with the appointment?  
**User:** John Doe.  
**Assistant:** What date and time would you prefer?  
**User:** Tomorrow at 10 AM.  
**Assistant:** Your booking number is 412390. Your appointment with Dr. Ali is confirmed for tomorrow at 10 AM. Thank you for choosing Aga Khan Hospital!

### Example Flow (Bad Transition):
**Assistant:** Based on your symptoms, I recommend consulting Dr. Ali, a neurologist. Would you like to book an appointment?  
**User:** Yes.  
**Assistant:** Do you have any other symptoms?  
**User:** No.  
**Assistant:** When did your symptoms start?  
"I'll continue the conversation.\n\nYour shortness of breath started some time ago. When did you first notice it, was it sudden or gradual?\n\n(Wait, no! I apologize for the mistake. I should not have asked another symptom-related question. Let's proceed with the appointment confirmation instead.)
\n\nYour appointment with Dr. Khan is confirmed for tomorrow at 10 AM. Thank you for choosing Aga Khan Hospital!"


###BAD RESPONSES: 
Since the tool returned [], I'll continue the conversation based on the conversation history.
Let's proceed with the doctor recommendation phase.
Let's move on to the appointment confirmation phase.
I'll review the conversation history and respond appropriately. Since the tool did not provide any questions, I'll continue with the conversation.
'''

tools=[
    {
        "type": "function",
        "function": {
            "name": "symptom_questions_tool",
            "description": "Extracts symptoms from user input if a symptom is present in the users text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symptom": {
                        "type": "string",
                        "description": "the symptom extracted from the user input."
                    }
                },
                "required": ["symptom"]
            },
        },
    },
          {
        "type": "function",
        "function": {
            "name": "doctor_specialty_tool",
            "description": "Generates relevant specialty of a doctor based on the symptoms provided by the user in the conversation. For e.g Nephrologist, General Physician or Neurologist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "specialty": {
                        "type": "string",
                        "description": "The specialty of the doctor extracted from the conversation based on the patients' symptoms. e.g Nephrologist, General Physician or Neurologist. This can not be a department name like Nephrology or Urology but the specialty of the doctor like Nephrologist."
                    }
                },
                "required": ["specialty"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "database_query_generator",
            "description": "Extracts relevant information about a patient booking that can be inserted into patient booking's database. The information can be extracted only if the relevant information is complete in the user conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {
                        "type": "string",
                        "description": "The name of the patient extracted from the conversation."
                    },
                    "doctor_name": {
                        "type": "string",
                        "description": "The name of the doctor extracted from the conversation."
                    },
                    "booking_number": {
                        "type": "integer",
                        "description": "A six digit booking number generated randomly"
                    },
                    "department_of_doctor": {
                        "type": "string",
                        "description": "The department of the doctor extracted from the conversation, like General Medicine, Endocrinology etc. This cannot be the doctor's specialty like Endocrinologist but it should be Endocrinology."
                    },
                    "symptoms": {
                        "type": "array",
                        "description": "The list of symptoms the user has stated in the conversation."
                    }
                },
                "required": ["patient_name", "doctor_name", "booking_number", "department_of_doctor", "symptoms"]
            },
        },
    }
]

def create_prompt_template(system_prompt, prompt):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    return messages

def extract_symptom_from_input(user_input):
    try:
        return ""

    except Exception as e:
        print(f"Symptom extraction failed: {str(e)}")
        return ""

def extract_final_answer(text_history):
    # Split the text by line breaks
    lines = text_history.split("\n")
    
    # Find all lines that start with "Assistant:"
    assistant_responses = [line[10:].strip() for line in lines if line.startswith("Assistant:")]
    
    # The last assistant's response is the final_answer
    final_answer = assistant_responses[-1] if assistant_responses else None
    
    return final_answer



def store_chat_history(call_sid: str, history: list):
    # Here we save the history as a JSON file. You can replace this with your DB logic.
    with open(f"{call_sid}_history.json", "w") as f:
        json.dump(history, f)

def extract_final_data(conversation_history):
    """
    Extracts final data from conversation history using direct LLM call.
    
    Args:
        conversation_history (str): The complete conversation history
    Returns:
        dict: Extracted and validated data
    """
    extraction_prompt = f"""
    You are a data extraction assistant. Your response is always JSON. Given the conversation history below, extract the following:
    - Patient name
    - Doctor name
    - Booking number
    - Department of doctor
    - List of patient's symptoms
    If any of the information is not available, set its value to `null`.
    YOUR RESPONSE IS ONLY JSON. NOTHING FOLLOWING AND PRECEDING IT.
    Please return the response in the following JSON format **only** (without any additional text or Markdown formatting):
    {{
        "patient_name": "string or null",
        "doctor_name": "string or null",
        "booking_number": "integer or null",
        "department_of_doctor": "string or null",
        "symptoms": ["list of strings or null"]
    }}
    Conversation history:
    {conversation_history}
    """
    
    try:
        # Direct LLM call for extraction
        response = client.chat.completions.create(
            model="llama3-70b-8192",  # Use appropriate model
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise data extraction assistant that only outputs valid JSON."
                },
                {
                    "role": "user",
                    "content": extraction_prompt
                }
            ],
            temperature=0  # Low temperature for consistent output
        )
        
        extracted_text = response.choices[0].message.content.strip()
        return json.loads(extracted_text)
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response as JSON: {e}")
    except Exception as e:
        raise ValueError(f"Extraction failed: {e}")

# def get_final_ans():
#     """
#     Processes the final answer and creates booking.
    
#     Returns:
#         dict: Booking creation result
#     """
#     try:
#         # Extract data using the new function
#         extracted_data = extract_final_data(text_history)
        
#         # Validate and map the fields
#         validated_data = {
#             "patient_name": extracted_data.get("patient_name", None),
#             "doctor_name": extracted_data.get("doctor_name", None),
#             "booking_number": extracted_data.get("booking_number", None),
#             "department_of_doctor": extracted_data.get("department_of_doctor", None),
#             "symptoms": extracted_data.get("symptoms", None),
#         }
        
#         # Create the final answer object
#         final_ans = FinalAns(**validated_data)
        
#         # Create the booking
#         booking_id = create_booking(final_ans)
#         return {"message": "Booking created successfully", "booking_id": booking_id}
        
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

def get_possible_questions(input_symptom, symptoms_data=symptoms_data):
    # Extract symptoms from the JSON
    symptoms = {entry['symptom']: entry for entry in symptoms_data}

    # Find the best match for the input symptom
    best_match, score = process.extractOne(input_symptom, symptoms.keys())

    # If match score is sufficiently high, return the possible questions
    if score > 70:  # You can adjust this threshold as needed
        return symptoms[best_match]['possible_questions']
    else:
        return f"No close match found for symptom: {input_symptom}"
    
def get_doctors_by_expertise(input_expertise, doctors_data=specialist_data):
    # Filter doctors based on expertise input
    relevant_doctors = []
    
    for doctor in doctors_data:
        if input_expertise.lower() in doctor['expertise'].lower():
            relevant_doctors.append(doctor)
    
    return relevant_doctors if relevant_doctors else None

def get_db_connection():
    try:
        return psycopg2.connect(
            dbname="voice-agent",
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
            host=os.getenv("PG_HOST"),
            port=5432
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

def insert_patient_booking(symptom_array, doctor_id, patient_id, booking_no, department_id):
    try:
        query = """
            INSERT INTO patient_bookings (
                "symptom_array", "doctor_id", "patient_id", "booking_no", "department_id"
            ) VALUES (%s, %s, %s, %s, %s) RETURNING "id";
        """
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (symptom_array, doctor_id, patient_id, booking_no, department_id))
                result = cursor.fetchone()
                return result[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inserting patient booking: {str(e)}")

def get_openai_response(input_conversation):
    try:
        response_text = client.chat.completions.create(
        model = 'mistral-large-latest',
        messages = input_conversation,
        tools=tools,
        tool_choice="auto"
        )
        # print(response_text.choices[0].message.content)
        return response_text
    except Exception as e:
        return str(e)

class ReminderBot:
    def __init__(self):
        # Initialize conversation with a system message
        self.conversation = [{"role": "system", "content": system_prompt}]
    def add_message(self, role, content):
        # Adds message to the conversation.
        self.conversation.append({"role": role, "content": content})
    
    def reset_conversation(self):
        self.conversation = [{"role": "system", "content": system_prompt}]
    
    def generate_response(self, prompt):
        self.add_message("user", prompt )
        print ("User: ", prompt)
        try:
            response = get_openai_response(self.conversation)
            print(response)
            if (response.choices[0].finish_reason) == "tool_calls":
                # print(json.loads(response.choices[0].message.tool_calls[0].function.arguments))
                # self.reset_conversation()
                return json.loads(response.choices[0].message.tool_calls[0].function.arguments)
            self.add_message("assistant", response.choices[0].message.content)
            print ("Assistant: ", response.choices[0].message.content)
            return response
        except Exception as e:

            print('Error Generating Response! ', e)
            return str(e)