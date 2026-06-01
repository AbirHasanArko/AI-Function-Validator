FROM python:3.10

# Set the working directory
WORKDIR /code

# Copy requirements and install
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the rest of the application
COPY . .

# Create the data directory so SQLite doesn't crash on read-only file systems
RUN mkdir -p /code/data

# Hugging Face Spaces exposes port 7860
ENV PORT=7860

# Run the FastAPI server
CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT
