from fastapi import HTTPException
import psycopg2
import os
from models import FinalAns, ChatSession
import threading  # to handle concurrent threads
from uuid import uuid4  # to generate unique call thread IDs
from twilio.rest import Client


# Simulate a in-memory store for call threads and history 
chat_sessions = {}


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


# Function to get doctor ID by name
def get_doctor_id(doctor_name):
    try:
        query = "SELECT id FROM doctors WHERE name = %s;"
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (doctor_name,))
                result = cursor.fetchone()
                return result[0] if result else None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving doctor ID: {str(e)}")


# Function to get department ID by name
def get_department_id(department_name):
    try:
        query = "SELECT id FROM departments WHERE department_name = %s;"
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (department_name,))
                result = cursor.fetchone()
                return result[0] if result else None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving department ID: {str(e)}")


# Function to get problem ID by description
def get_problem_id(description):
    try:
        query = "SELECT id FROM problems WHERE description = %s;"
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (description,))
                result = cursor.fetchone()
                return result[0] if result else None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving problem ID: {str(e)}")


# Function to get patient ID by name
def get_patient_id(patient_name,age):
    try:
        select_query = "SELECT id FROM patients WHERE name = %s;"
        insert_query = "INSERT INTO patients (name,age) VALUES (%s,%s) RETURNING id;"
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check if the patient already exists
                cursor.execute(select_query, (patient_name,))
                result = cursor.fetchone()

                if result:
                    return result[0]  # Return existing patient ID

                # Insert the new patient and retrieve the new ID
                cursor.execute(insert_query, (patient_name,age))
                new_patient_id = cursor.fetchone()[0]
                conn.commit()  # Commit the transaction to save changes
                return new_patient_id
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving or creating patient ID: {str(e)}")


# Function to insert into patient_bookings
def insert_patient_booking(symptom_array, doctor_id, patient_id, booking_no, department_id, call_sid):
    try:
        query = """
            INSERT INTO patient_bookings (
                "symptom_array", "doctor_id", "patient_id", "booking_no", "department_id", "call_sid"
            ) VALUES (%s, %s, %s, %s, %s, %s) RETURNING "id";
        """
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (symptom_array, doctor_id, patient_id, booking_no, department_id,call_sid))
                result = cursor.fetchone()
                return result[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inserting patient booking: {str(e)}")


def process_patient_booking(final_ans: FinalAns, call_sid):
    try:
        patient_id = get_patient_id(final_ans.patient_name, final_ans.age)
        if patient_id is None:
            raise ValueError(f"Patient '{final_ans.patient_name}' not found.")
        else: 
            print('Fetched patient ID')
        
        doctor_id = get_doctor_id(final_ans.doctor_name)
        if doctor_id is None:
            raise ValueError(f"Doctor '{final_ans.doctor_name}' not found.")
        else: 
            print('Fetched Doctor ID')
        
        department_id = get_department_id(final_ans.department_of_doctor)
        if department_id is None:
            raise ValueError(f"Department '{final_ans.department_of_doctor}' not found.")
        else: 
            print('Fetched department ID')
        
        print(final_ans.symptoms)
        print('Booking number', final_ans.booking_number)

        booking_id = insert_patient_booking(
            symptom_array=final_ans.symptoms,
            doctor_id=doctor_id,
            patient_id=patient_id,
            booking_no=final_ans.booking_number,
            department_id=department_id,
            call_sid=call_sid
        )
        return booking_id
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing patient booking: {str(e)}")


def create_booking(final_ans: FinalAns):
    try:
        booking_id = process_patient_booking(final_ans)
        return {"message": "Booking created successfully", "booking_id": booking_id}
    except HTTPException as e:
        raise e  # Re-raise the HTTPException to preserve its status code and detail
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")






''' Function to initialize a call thread and start storing chat history
# def create_call_thread():
#    thread_id = str(uuid4())  # Generate a unique thread ID
#    call_threads[thread_id] = {
#        "history": [],
#        "thread_id": thread_id,
#        "active": True
#    }
#    return thread_id

#Function to log message into the active call thread's history
def log_message_to_thread(thread_id, message):
    if thread_id in call_threads and call_threads[thread_id]["active"]:
        call_threads[thread_id]["history"].append(message)
    else:
        raise HTTPException(status_code=404, detail="Thread not found or inactive.") 


#Function to clear the chat history when the call ends
def clear_call_thread(thread_id):
    if thread_id in call_threads:
        call_threads[thread_id]["history"].clear()
        call_threads[thread_id]["active"] = False  # Mark the thread as inactive
    else:
        raise HTTPException(status_code=404, detail="Thread not found.")


# Endpoint to end the call and clear the history
def end_call(thread_id):
    try:
        clear_call_thread(thread_id)
        return {"message": f"Call with thread {thread_id} ended and history cleared."}
    except HTTPException as e:
        raise e  # Re-raise the exception if the thread is not found
'''

def get_or_create_chat_session(sid: str):
#     """
#     Retrieve an existing ChatHistory or create a new one if not found.
#     """
#     with lock:
        if sid not in chat_sessions:
            chat_sessions[sid] = ChatSession(sid)
        return chat_sessions[sid]

def log_message(sid, role, message):
    session = get_or_create_chat_session(sid)
    session.add_message(role, message)

def reset_session(sid):
    if sid in chat_sessions:
        chat_sessions[sid].reset_conversation()
    else:
        raise ValueError(f"Session with id {sid} not found.")
    
def end_session(sid):
    if sid in chat_sessions:
        del chat_sessions[sid]
    else:
        raise ValueError(f"Session with id {sid} not found.")


