
import openai
import os

# Load your API key from environment variable
groq_key = os.getenv('GROQ_KEY')

# Set up your OpenAI API client
openai.api_key = groq_key

def call_llm(prompt):
    try:
        # Call to OpenAI's chat completion endpoint
        response = openai.ChatCompletion.create(
            model="llama3-groq-70b-8192-tool-use-preview",  # replace with your model name
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        # Extract and return the response content
        assistant_response = response['choices'][0]['message']['content']
        return assistant_response
    except Exception as e:
        print("Error occurred while calling the LLM:", e)
        return str(e)

# Sample prompt to test
sample_prompt = "Hello, can you assist me with my symptoms?"

# Call the function to check if it works and print the result
response = call_llm(sample_prompt)
print("LLM Response:", response)
