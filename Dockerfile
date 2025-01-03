# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file for FastAPI API from the correct directory
COPY ./groq/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Node.js (latest LTS 20.x) and Yarn in a single step
RUN apt-get update && apt-get install -y curl gnupg && \
    curl -sL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - && \
    echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list && \
    apt-get update && apt-get install -y yarn && \
    rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code into the container
COPY . .

# Install Node.js dependencies and build the Node.js application
RUN yarn install && yarn build

# Install concurrently globally using npm
RUN npm install -g concurrently

# Set the working directory to /app/groq for the FastAPI app
WORKDIR /app/groq

# Expose ports for FastAPI and Node.js apps
EXPOSE 4000 3001

# Use concurrently to run both FastAPI and Node.js apps in the foreground
CMD ["concurrently", "uvicorn llm:app --host 0.0.0.0 --port 8000", "node /app/dist/index.js"]
