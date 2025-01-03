
import requests

url = "http://127.0.0.1:4000/create-booking/"
data = {
    "patient_name": "Hamna Inam",
    "doctor_name": "Dr. Jamshed Alam",
    "booking_number": 421576,
    "department_of_doctor": "Endocrinology",
    "symptoms": [
        "Constant sharp headache",
        "Sensitivity to light and sound",
        "Blurred vision",
        "Fatigue",
        "Dizziness",
        "Fatigue"
    ]
}

response = requests.post(url, json=data)

if response.status_code == 200:
    print("Success:", response.json())
else:
    print("Error:", response.text)