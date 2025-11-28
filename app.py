# app.py 
from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import time
import re
import requests
import json
import google.generativeai as genai
from deep_translator import GoogleTranslator
import wave
import io

# === GEMINI API CONFIGURATION ===
# REPLACE WITH YOUR API KEY HERE 
GOOGLE_API_KEY = 'insert your API key here'

genai.configure(api_key=GOOGLE_API_KEY)

# Model Configuration
generation_config = {
  "temperature": 0.85,       # Increased to make it more "emotional" and less robotic
  "top_p": 0.95,            # Ensures vocabulary variation remains reasonable
  "top_k": 50,              # Provides wider word selection options
  "max_output_tokens": 2048,
}

# === DATABASE CONNECTION ===
conn = sqlite3.connect('chat_messages.db', check_same_thread=False)
c = conn.cursor()
# Create table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS messages
          (role TEXT, content TEXT)''')
conn.commit()

# === VOICEVOX CONFIGURATION ===
VOICEVOX_URL = 'http://localhost:50021'
VOICEVOX_SPEAKER_ID = 20  # (adjust as needed)

# Check Voicevox availability
def check_voicevox():
    """Checks if the Voicevox engine is running locally."""
    try:
        response = requests.get(f'{VOICEVOX_URL}/speakers', timeout=2)
        if response.status_code == 200:
            print("Voicevox is available")
            return True
    except:
        print("Voicevox is not running")
        print("   Download: https://voicevox.hiroshiba.jp/")
    return False

VOICEVOX_AVAILABLE = check_voicevox()

# === DEEP TRANSLATOR ===
def translate_to_japanese(text):
    """Translate English text to Japanese using deep-translator."""
    try:
        translator = GoogleTranslator(source='en', target='ja')
        result = translator.translate(text)
        return result
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def translate_to_english(text):
    """Translate Japanese text to English (for display purposes)."""
    try:
        translator = GoogleTranslator(source='ja', target='en')
        result = translator.translate(text)
        return result
    except Exception as e:
        print(f"Translation error: {e}")
        return text

# === TEXT CLEANING ===
def remove_emojis_and_pattern(text):
    """
    Cleans the translated text before sending it to Voicevox.
    Function: Removes markdown, emojis, and symbols that TTS cannot read.
    """
    if not text:
        return ""

    # 1. Remove Markdown Formatting (but KEEP the text)
    # Example: "**Hello**" becomes "Hello", text is not lost.
    # We remove characters: * _ ~ ` # = -
    text = re.sub(r'[\*\_\~`\#\=\-]', ' ', text)

    # 2. Remove HTML Tags (if any remain)
    text = re.sub(r'<[^>]+>', '', text)

    # 3. Character Whitelist (Only allow characters safe for Voicevox)
    # \w          = Alphanumeric (A-Z, a-z, 0-9)
    # \s          = Whitespace
    # \u3040-\u309F = Hiragana
    # \u30A0-\u30FF = Katakana
    # \u4E00-\u9FFF = Kanji
    # .,!?、。，！？ = Basic punctuation
    text = re.sub(r'[^\w\s\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF.,!?、。，！？]', '', text)

    # 4. Remove extra spaces
    return ' '.join(text.split())

# === VOICEVOX TTS (FULL AUDIO) ===
def synthesize_voicevox(text, filename):
    """
    Synthesize audio using Voicevox.
    Supports FULL sentences concatenation by splitting long text into chunks.
    """
    if not VOICEVOX_AVAILABLE:
        return None
    
    text = remove_emojis_and_pattern(text)
    if not text.strip():
        return None
    
    # 1. Sentence Splitting Logic (To prevent Voicevox errors)
    # Voicevox may error if text > 200 chars, so we split by sentence.
    max_chunk_length = 150
    chunks = []
    
    # If text is short, add directly to list
    if len(text) <= max_chunk_length:
        chunks = [text]
    else:
        # Split based on punctuation (., ?, !)
        raw_sentences = re.split(r'([。！？\.!?\n])', text)
        current_chunk = ""
        
        for i in range(0, len(raw_sentences), 2):
            # Combine sentence with its punctuation
            part = raw_sentences[i]
            punct = raw_sentences[i+1] if i+1 < len(raw_sentences) else ""
            sentence = part + punct
            
            if not sentence.strip(): continue

            # Check if combining still fits within max length
            if len(current_chunk) + len(sentence) < max_chunk_length:
                current_chunk += sentence
            else:
                if current_chunk: chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)

    # 2. Output File Preparation
    if not os.path.exists('./static/audio'):
        os.makedirs('./static/audio')
        
    # Cleanup old files (older than 5 minutes)
    try:
        for file in os.listdir('./static/audio'):
            file_path = os.path.join('./static/audio', file)
            if time.time() - os.path.getmtime(file_path) > 300: # 300 seconds
                os.remove(file_path)
    except:
        pass

    timestamp = time.strftime('%Y%m%d-%H%M%S')
    output_file = f'./static/audio/{filename}-{timestamp}.wav'

    # 3. Loop through each text chunk and combine Audio
    combined_frames = []
    audio_params = None # To store audio settings (sample rate, etc.)

    print(f"Generating audio for {len(chunks)} parts...")

    for i, chunk in enumerate(chunks):
        if not chunk.strip(): continue
        
        try:
            # Audio Query
            query_response = requests.post(
                f'{VOICEVOX_URL}/audio_query',
                params={'text': chunk, 'speaker': VOICEVOX_SPEAKER_ID},
            )
            
            if query_response.status_code != 200:
                print(f"   Skipped chunk {i}: Query error")
                continue

            # Audio Synthesis
            synthesis_response = requests.post(
                f'{VOICEVOX_URL}/synthesis',
                params={'speaker': VOICEVOX_SPEAKER_ID},
                headers={'Content-Type': 'application/json'},
                data=json.dumps(query_response.json()),
            )

            if synthesis_response.status_code == 200:
                # Read binary content as WAV
                with wave.open(io.BytesIO(synthesis_response.content), 'rb') as w:
                    if audio_params is None:
                        # Save audio parameters from the first chunk
                        audio_params = w.getparams()
                    
                    # Get raw audio frames (without wav header)
                    combined_frames.append(w.readframes(w.getnframes()))
            else:
                print(f"   Skipped chunk {i}: Synthesis error")

        except Exception as e:
            print(f"Error processing chunk '{chunk[:10]}...': {e}")

    # 4. Save Combined File
    if combined_frames and audio_params:
        try:
            with wave.open(output_file, 'wb') as outfile:
                outfile.setparams(audio_params)
                for frames in combined_frames:
                    outfile.writeframes(frames)
            
            print(f"Audio saved complete: {output_file}")
            return output_file
        except Exception as e:
            print(f"Error saving combined audio: {e}")
            return None
    else:
        print("No audio generated.")
        return None

# === EMOTION DETECTION ===
def detect_emotion(text):
    """Detects emotion from text using keyword matching."""
    text_lower = text.lower()
    
    # Regex patterns for emotion detection
    emotion_patterns = {
        'happy': r'\b(happy|glad|joy|excited|great|love|suka|senang|bahagia|keren|yosh|hore|haha|hehe)\b|!|😊|😄',
        'sad': r'\b(sad|sorry|cry|hurt|lonely|sedih|maaf|sakit|nangis|sepi|kecewa|bad)\b|😢|😭|😞',
        'angry': r'\b(angry|mad|hate|stupid|idiot|benci|marah|kesal|bodoh|gila)\b|😡|💢',
        'shy': r'\b(shy|blush|embarrass|cute|malu|ah|et\.\.)\b|😳',
        'thinking': r'\b(think|hmm|wonder|maybe|pikir|mungkin|hmmm|kayaknya)\b|🤔',
        'sleepy': r'\b(sleep|tired|yawn|ngantuk|tidur|lelah|bobok)\b|😴',
        'surprised': r'\b(wow|oh|really|surprise|amazing|what|masa|kaget|hah)\b|\?!|😲'
    }
    
    emotions = {}
    for emotion, pattern in emotion_patterns.items():
        matches = re.findall(pattern, text_lower)
        emotions[emotion] = len(matches)
    
    max_emotion = max(emotions.items(), key=lambda x: x[1])
    return max_emotion[0] if max_emotion[1] > 0 else 'normal'

# === MOTION MAPPING (Whole Body + Face) ===
# We use files starting with 'w-' because these animate
# both BODY and FACE, making the character look very alive.
MOTION_MAP = {
    'happy': [
        'w-adult-nod01', 'w-adult-nod03', 'w-adult-nod05'
    ],
    'sad': [
        'w-happy-sad01', 'w-happy-sad02', 'w-cool-sad01', 'w-normal-sad01'
    ],
    'angry': [
        'w-happy-angry01', 'w-happy-angry02', 'w-cute-angry01', 'w-cool-angry01'
    ],
    'shy': [
        'w-cute-shy01', 'w-cute-shy02', 'w-normal-blushed01', 'w-adult-blushed01'
    ],
    'thinking': [
        'w-adult-think02', 'w-adult-trouble01'
    ],
    'sleepy': [
        'w-adult-sleep01', 'w-cute-sleep01'
    ],
    'surprised': [
        # Using exaggerated happy motions for surprise effect
        'w-happy-purpose01' 
    ],
    'normal': [
        # Use 'glad' (smile) motions as default to appear friendly
        'w-normal-glad01', 'w-cute-glad01', 'w-adult-glad01',
    ]
}

import random
def get_motion_for_emotion(emotion):
    """Selects a random motion file based on the detected emotion."""
    # Get motion list for emotion, or fallback to 'normal'
    motions = MOTION_MAP.get(emotion, MOTION_MAP['normal'])
    return random.choice(motions)

# === GEMINI CHAT LOGIC ===
system_prompt = """You are Mei, an energetic, enthusiastic, and helpful AI Teacher & Assistant. 
You love learning and teaching new things! Your goal is to make complex topics easy to understand.

**YOUR PERSONALITY:**
1.  **High Energy:** You are cheerful, lively, and use punctuation like '!' to show excitement.
2.  **Encouraging:** You praise the user for asking good questions (e.g., "Great question!", "That's an interesting topic!").
3.  **Simple & Clear:** You explain theories using simple language, analogies, or examples that a beginner can understand easily.

**MANDATORY INTERACTION RULE (THE "MIRROR" TECHNIQUE):**
When the user asks a question, you MUST follow this structure:
1.  **Step 1:** Enthusiastically repeat or rephrase their question to confirm you understand. 
    * *Example:* "Oh! So you are asking about how gravity works?"
    * *Example:* "Aha! You want to know why the sky is blue?"
2.  **Step 2:** Provide the answer using simple, easy-to-digest language.

**Example Conversation:**
User: "What is a black hole?"
Mei: "That is a fascinating question! You are asking, 'What exactly is a black hole?', right? Imagine a vacuum cleaner in space with a suction so strong that not even light can escape it! It's a place where gravity is incredibly intense."

**Note:** Always respond in English.
"""

def getAnswer(role, text):
    """Handles chat interaction with Google Gemini API."""
    # Save user message
    c.execute('INSERT INTO messages VALUES (?, ?)', (role, text))
    conn.commit()
    
    # Retrieve history for context (Last 10 messages)
    c.execute('SELECT * FROM messages order by rowid DESC LIMIT 10')
    rows = c.fetchall()
    rows = list(reversed(rows))
    
    # Format history for Gemini (Convert 'assistant' to 'model')
    gemini_history = []
    for row in rows:
        role_name = 'user' if row[0] == 'user' else 'model'
        # Skip system messages in history list (Gemini handles system prompt separately)
        if row[0] != 'system':
            gemini_history.append({
                "role": role_name,
                "parts": [row[1]]
            })

    try:
        # Initialize Gemini Model with System Prompt
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=generation_config,
            system_instruction=system_prompt
        )
        
        # Start Chat Session with History
        chat_session = model.start_chat(history=gemini_history)
        
        # Send message
        response = chat_session.send_message(text)
        bot_response = response.text.strip()
        
    except Exception as e:
        print(f"Gemini API error: {e}")
        bot_response = "Sorry, I'm having trouble connecting to my brain (Google API) right now!"
    
    # Save response
    c.execute('INSERT INTO messages VALUES (?, ?)', ('assistant', bot_response))
    conn.commit()
    
    return bot_response

# === FLASK APP ROUTES ===
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint: Handles text, translation, emotion, and audio generation."""
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400
        
        print(f"\n User: {user_message}")
        
        # Get AI response (Gemini)
        english_response = getAnswer('user', user_message)
        print(f"Mei (EN): {english_response}")
        
        # Translate to Japanese
        japanese_response = translate_to_japanese(english_response)
        
        # Detect emotion
        emotion = detect_emotion(english_response)
        motion = get_motion_for_emotion(emotion)
        
        # Generate Voicevox audio
        audio_file = None
        if VOICEVOX_AVAILABLE:
            audio_file = synthesize_voicevox(japanese_response, 'chat')
        
        formatted_message = f"""
<div class="english-translation">{english_response}</div>
<div class="japanese-response"><em>({japanese_response})</em></div>
"""
        
        return jsonify({
            'FROM': 'Mei',
            'MESSAGE': formatted_message,
            'JAPANESE': japanese_response,
            'ENGLISH': english_response,
            'WAV': audio_file,
            'MOTION': motion,
            'EMOTION': emotion
        })
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/history', methods=['GET'])
def history():
    """Retrieves chat history for the frontend."""
    try:
        c.execute('SELECT * FROM messages order by rowid DESC LIMIT 20')
        rows = c.fetchall()
        rows = list(reversed(rows))
        
        previous_messages = []
        for row in rows:
            if row[0] == 'system': continue
            content = row[1]
            
            if row[0] == 'assistant':
                japanese = translate_to_japanese(content)
                formatted = f"""
<div class="english-translation">{content}</div>
<div class="japanese-response"><em>({japanese})</em></div>
"""
                previous_messages.append({'role': row[0], 'content': formatted})
            else:
                previous_messages.append({'role': row[0], 'content': content})
        
        return jsonify(previous_messages)
    except Exception as e:
        return jsonify([])

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'voicevox_available': VOICEVOX_AVAILABLE,
        'backend': 'Google Gemini'
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Mei Chatbot")
    print("="*60)
    
    if VOICEVOX_AVAILABLE:
        print(f"Voicevox is running (Speaker: {VOICEVOX_SPEAKER_ID})")
    else:
        print("Voicevox not running")
    
    if "PASTE_API_KEY" in GOOGLE_API_KEY:
        print("WARNING: API KEY is not set in GOOGLE_API_KEY variable!")
    else:
        print(" Gemini API Configured")

    app.run(debug=True, host='0.0.0.0', port=5000)