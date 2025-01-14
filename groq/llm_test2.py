import requests
import os

# Load your API key from environment variable
groq_key = os.getenv('GROQ_KEY')

# Endpoint for your API
endpoint = "http://localhost:4000/chat"  # Replace with your actual endpoint

def call_llm(prompt):
    try:
        # Set up the payload for the API request
        payload = {
            "prompt": prompt
        }
        
        # Set up the headers with the API key for authorization
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }

        # Make the request to the LLM API
        response = requests.post(endpoint, json=payload, headers=headers)

        # Check if the response status code is 200 (OK)
        if response.status_code == 200:
            # Log the entire response to see what it looks like
            print("Raw Response:", response.json())  # Print the raw response to debug

            # Get the response data
            assistant_response = response.json()

            if isinstance(assistant_response, dict) and 'response' in assistant_response:
                error_message = assistant_response['response']
                return f"Error from API: {error_message}"

            # Assuming the response is a dictionary and contains 'choices'
            if isinstance(assistant_response, dict) and 'choices' in assistant_response:
                return assistant_response['choices'][0]['message']['content']
            else:
                return "Response does not have the expected structure"

        else:
            return f"Error: Received status code {response.status_code} - {response.text}"

    except Exception as e:
        print("Error occurred while calling the LLM:", e)
        return str(e)

# Sample prompt to test
sample_prompt = "Hello, can you assist me with my symptoms?"

# Call the function to check if it works and print the result
response = call_llm(sample_prompt)
print("LLM Response:", response)
