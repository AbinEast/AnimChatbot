# Live2D AI Chatbot 

A web-based interactive chatbot featuring a Live2D avatar that responds with dynamic motions and voice. This project integrates **Flask** for the backend, **Google Gemini AI** for conversation logic, and **PixiJS** for rendering the Live2D model.

##  Features

* **Interactive Live2D Avatar:** Uses the Kohane model which reacts with specific animations (greeting, nodding, etc.) based on the context.
* **AI-Powered Conversation:** Integrated with Google Gemini API for intelligent responses.
* **Voice Support:** The avatar syncs with audio responses (Voice capabilities).
* **Chat History:** Saves and loads conversation history using SQLite.
* **Dynamic Expressions:** The avatar changes expressions (Joy, Anger, Sorrow, etc.) based on the chat sentiment.

## Tech Stack

* **Backend:** Python, Flask
* **Frontend:** HTML5, CSS3, JavaScript
* **Live2D Rendering:** PixiJS, Pixi-Live2D-Display
* **AI Model:** Google Generative AI (Gemini)
* **TTS Engine:** Voicevox (Local Server)
* **Database:** SQLite

##  Project Structure

```text
Bot_project/
├── app.py                  # Main Flask application
├── chat_messages.db        # SQLite database for chat history
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html          # Main frontend interface
└── static/
    ├── css/
    │   └── style.css       # Styling
    ├── js/
    │   └── main.js         # Frontend logic & Live2D controller
    ├── model/              # Live2D Model assets (Kohane)
    └── audio/              # Generated audio files
```

## Create a Virtual Environment (Optional but recommended)
```
python -m venv venv
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```
## Install Dependencies
```
pip install -r requirements.txt
```

## IMPORTANT: Setup Voicevox (Required for Audio)
This project requires the Voicevox Engine to be running locally to generate audio.

- Download Voicevox: Go to https://voicevox.hiroshiba.jp/ and download the software for your OS.

- Run Voicevox: Open the Voicevox application. It will automatically start a local server at http://localhost:50021.

Note: Keep the Voicevox app open while running the chatbot.

## Configuration (Optional)
You can change the speaker ID in app.py if you want a different voice
```
VOICEVOX_SPEAKER_ID = 20  # Change this ID for different characters 
```

## Setup Google API Key
Set your Google Gemini API Key in app.py or use environment variables:
```
GOOGLE_API_KEY = "YOUR_OWN_API_KEY"
```

## Run the Application
```
python app.py
```

## Usage
- Ensure Voicevox is running in the background.
- Open the web page.
- Type a message in the input box (English).
- The character will reply with Voice, text, and a matching motion
