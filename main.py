from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from transformers import T5ForConditionalGeneration, T5Tokenizer
from PyPDF2 import PdfReader
import os
import torch
import sqlite3
import uuid
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

model_name = "google/flan-t5-small"  
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)

DB_FILE = "pdf_chatbot.db"

def initialize_db():
    """
    Initialize SQLite database and create necessary tables if they don't exist.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            filename TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

initialize_db()  

uploaded_pdf_content = ""

def extract_pdf_content(pdf_file_path: str) -> str:
    """
    Extract text content from a PDF file.

    Args:
        pdf_file_path (str): Path to the PDF file.

    Returns:
        str: Extracted text content.
    """
    try:
        reader = PdfReader(pdf_file_path)
        content = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        return content.strip()
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def store_pdf_in_db(pdf_content: str, filename: str):
    """
    Store extracted PDF content in SQLite database.

    Args:
        pdf_content (str): Text content of the PDF.
        filename (str): Name of the uploaded file.
    """
    try:
        unique_id = str(uuid.uuid4()) 
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO documents (id, content, filename) VALUES (?, ?, ?)",
                       (unique_id, pdf_content, filename))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error storing document in database: {e}")

def get_model_response(prompt: str) -> str:
    """
    Generate a conversational response using the Flan-T5 model.

    Args:
        prompt (str): User's input.

    Returns:
        str: Generated response from the model.
    """
    global uploaded_pdf_content
    try:
        combined_prompt = f"{uploaded_pdf_content}\n\nUser: {prompt}\nBot:"
        inputs = tokenizer.encode(combined_prompt, return_tensors="pt", max_length=512, truncation=True)
        outputs = model.generate(inputs, max_length=150, num_beams=5, early_stopping=True)
        return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
    except Exception as e:
        print(f"Error generating response: {e}")
        return "An error occurred while generating a response."

@app.get("/")
async def get():
    """
    Serve the main chat HTML page.
    """
    return HTMLResponse(content=open("static/chat.html").read())

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Handle PDF uploads and extract/store content.

    Args:
        file (UploadFile): Uploaded PDF file.

    Returns:
        JSONResponse: Success or failure message.
    """
    global uploaded_pdf_content
    try:
        file_location = f"static/{file.filename}"
        with open(file_location, "wb") as f:
            f.write(file.file.read())
        
        uploaded_pdf_content = extract_pdf_content(file_location)
        store_pdf_in_db(uploaded_pdf_content, file.filename)
        os.remove(file_location)  
        return JSONResponse({"message": "PDF uploaded and content extracted successfully."}, status_code=200)
    except Exception as e:
        return JSONResponse({"message": f"Error uploading PDF: {e}"}, status_code=500)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time communication.

    Args:
        websocket (WebSocket): WebSocket connection object.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            print("Received message from client:", data)

            result_text = get_model_response(data)
            print("Generated response:", result_text)

            await websocket.send_text(result_text)
    except WebSocketDisconnect:
        print("Client disconnected")
