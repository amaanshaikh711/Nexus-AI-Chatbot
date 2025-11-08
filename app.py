import os
import google.generativeai as genai
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

# --- Environment Setup ---
load_dotenv()

# --- Sanity Check ---
CWD = os.getcwd() 
print(f"--- Nexus AI Boot Check ---")
print(f"Current Working Directory: {CWD}")

TEMPLATE_DIR = os.path.join(CWD, 'templates')
STATIC_DIR = os.path.join(CWD, 'static')

if not os.path.isdir(TEMPLATE_DIR):
    print("="*50)
    print(f"CRITICAL ERROR: 'templates' folder not found at: {TEMPLATE_DIR}")
    print("SOLUTION: 'cd' into your 'nexus_ai' folder and run 'python app.py' from there.")
    print("="*50)
    exit()
else:
    print(f"SUCCESS: Found 'templates' folder.")

if not os.path.isdir(STATIC_DIR):
    print("="*50)
    print(f"CRITICAL ERROR: 'static' folder not found at: {STATIC_DIR}")
    print("SOLUTION: 'cd' into your 'nexus_ai' folder and run 'python app.py' from there.")
    print("="*50)
    exit()
else:
    print(f"SUCCESS: Found 'static' folder.")
print(f"---------------------------")

# --- Configuration ---

# 1. Set up Flask
app = Flask(__name__,
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)
            
# A secret key is required for Flask sessions
app.secret_key = os.urandom(24) 

# 2. Configure the Gemini API
API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-09-2025")
if not API_KEY:
    print("="*50)
    print("CRITICAL ERROR: GEMINI_API_KEY not found in the environment.")
    print("SOLUTION: Make sure you have a '.env' file with 'GEMINI_API_KEY=your_key_here'.")
    print("You can also set GEMINI_MODEL to a model that exists for your account: e.g. GEMINI_MODEL=chat-bison-001")
    print("="*50)
    exit()

model = None
try:
    genai.configure(api_key=API_KEY)
    try:
        # Try to instantiate the configured model name (can fail if model not available)
        model = genai.GenerativeModel(GEMINI_MODEL)
        print(f"Model '{GEMINI_MODEL}' loaded successfully.")
    except Exception as inner_e:
        # If the specific model cannot be used, try listing available models and show guidance
        print(f"Requested model '{GEMINI_MODEL}' failed to load: {inner_e}")
        print("Attempting to list available models to help you choose a supported one...")
        try:
            available = genai.list_models()
            print("Available models returned by the API:")
            # Attempt to print a compact list (structure may vary by package version)
            if isinstance(available, (list, tuple)):
                for m in available:
                    # try to print id/name fields if present, else print repr
                    if isinstance(m, dict):
                        print(" -", m.get('name') or m.get('id') or m)
                    else:
                        print(" -", getattr(m, 'name', getattr(m, 'id', str(m))))
            else:
                print(available)
            print("Set the GEMINI_MODEL environment variable to one of the above model identifiers and restart the app.")
        except Exception as list_e:
            print(f"Could not list models: {list_e}")
            print("If you're using Google Cloud Generative AI, ensure your API key and permissions are correct.")
        model = None
except Exception as e:
    print(f"Error configuring Gemini API client: {e}")
    model = None

# --- Helper Functions ---

def get_gemini_response(chat_history):
    """
    Sends the chat history to the Gemini API and gets a response.
    """
    if not model:
        return "Error: Gemini model is not initialized. Check API key and configuration."

    try:
        # Build the conversation history as a string
        conversation = ""
        for item in chat_history[:-1]:  # Exclude the last user message
            role = item['role']
            parts = item['parts']
            conversation += f"{role}: {' '.join(parts)}\n"

        # Add the last user message
        last_user_message = chat_history[-1]['parts'][0] if chat_history else ""
        conversation += f"user: {last_user_message}\n"

        # Generate response
        response = model.generate_content(conversation)
        
        # Clean up the response text
        cleaned_text = response.text.replace('*', '').replace('|', '').replace('\n', '<br>')
        
        return cleaned_text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return f"Error: Could not connect to Nexus AI. Please try again. ({e})"

# --- Flask Routes ---

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main chat route.
    - GET: Displays the chat interface with the current chat history.
    - POST: Processes a new user message, gets a response, and updates the history.
    """
    
    # Initialize chat history in the session if it doesn't exist
    if 'chat_history' not in session:
        # Start with a friendly welcome message from the AI
        session['chat_history'] = [
            {
                'role': 'model',
                'parts': ['Hi! I’m Nexus AI — your intelligent assistant. How can I help you today?']
            }
        ]
    
    # Handle POST request (when user sends a message)
    if request.method == 'POST':
        user_message_text = request.form['message']
        
        if user_message_text: # Process only if the message is not empty
            
            # 1. Get current history and add the user's message
            current_history = session['chat_history']
            current_history.append({'role': 'user', 'parts': [user_message_text]})
            
            # 2. Get the AI's response
            ai_response_text = get_gemini_response(current_history)
            
            # 3. Add the AI's response to the history
            current_history.append({'role': 'model', 'parts': [ai_response_text]})
            
            # 4. Save the updated history back to the session
            session['chat_history'] = current_history
            
        # Redirect back to the GET route to display the updated chat
        return redirect(url_for('index'))

    # Handle GET request (display the page)
    chat_history_display = session.get('chat_history', [])
    
    try:
        return render_template('index.html', chat_history=chat_history_display)
    except Exception as e:
        print("="*50)
        print(f"CRITICAL ERROR: Failed to render 'index.html'.")
        print(f"Error: {e}")
        print("Please check that 'index.html' is inside your 'templates' folder.")
        print("="*50)
        return "Error: Template not found. Check terminal for details.", 500


@app.route('/clear')
def clear_chat():
    """
    Clears the chat history from the session.
    """
    session.pop('chat_history', None)
    return redirect(url_for('index'))

# --- Run the Application ---

if __name__ == '__main__':
    print("Starting Nexus AI Flask server...")
    print("Access the chatbot at: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)