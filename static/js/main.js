window.onload = function () {
    
console.log("🚀 App starting...");

// Global Variables
const messages = document.querySelector('.message-list');
const btn = document.querySelector('.btn');
const input = document.querySelector('input');

const volume = 1;
const expression = 4;
const resetExpression = true;
const crossOrigin = "anonymous";
let model;

// Check if PIXI and live2d libraries are loaded correctly
console.log("PIXI loaded:", typeof PIXI !== 'undefined');
console.log("PIXI.live2d loaded:", typeof PIXI?.live2d !== 'undefined');

if (typeof PIXI === 'undefined') {
    console.error("❌ PIXI not loaded! Check script tags.");
}

// === LIVE2D & PIXI SETUP ===
if (typeof PIXI !== 'undefined') {
    window.PIXI = PIXI;
    const live2d = PIXI.live2d;

    // Load Live2D Model asynchronously
    (async function () {
        const canvas_container = document.getElementById('canvas_container');
        
        // Check if container exists in HTML
        if (!canvas_container) {
            console.error("❌ Canvas container not found!");
            return;
        }
        
        console.log("✅ Container found. Size:", canvas_container.offsetWidth, "x", canvas_container.offsetHeight);
        
        // Show loading indicator inside canvas container
        canvas_container.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: rgba(255,255,255,0.8); text-align: center;">
                <div>
                    <div style="font-size: 48px; margin-bottom: 10px;">⏳</div>
                    <div style="font-size: 14px;">Loading Model...</div>
                </div>
            </div>
        `;
        
        // Initialize PIXI Application
        const app = new PIXI.Application({
            view: document.getElementById('canvas'),
            autostart: true,
            height: canvas_container.offsetHeight,
            width: canvas_container.offsetWidth,
            backgroundAlpha: 0.0, // Transparent background
            antialias: true,
            resolution: window.devicePixelRatio || 1
        });
        
        // Clear loading indicator and attach PIXI view
        canvas_container.innerHTML = '';
        canvas_container.appendChild(app.view);
        
        try {
            console.log("🎨 Loading Live2D model...");
            
            // Load the Cubism 3 Model
            model = await live2d.Live2DModel.from(
                'static/model/kohane/09kohane_longunit_3_f_t04.model3.json', 
                { autoInteract: false } // Disable auto-interactions (we control it via code)
            );

            app.stage.addChild(model);
            
            console.log("✅ Model loaded! Size:", model.width, "x", model.height);
            
            // Calculate scale to fit container while maintaining aspect ratio
            const scaleX = canvas_container.offsetWidth / model.width;
            const scaleY = canvas_container.offsetHeight / model.height;
            const scale = Math.min(scaleX, scaleY) * 0.8; // 0.8 to add some padding
            
            // Center and position the model
            model.anchor.set(0.5, 0.5);
            model.x = canvas_container.offsetWidth / 2;
            model.y = canvas_container.offsetHeight / 2 + 50; // Slight offset down
            model.scale.set(0.18)
            
            // Play initial greeting motion
            try {
                model.motion("w-normal-greeting01");
                console.log("✅ Greeting motion played");
            } catch(e) {
                console.warn("⚠️ Motion failed:", e.message);
            }
            
            console.log("🎉 Model setup complete!");
        } catch(e) {
            console.error("❌ Model loading error:", e);
            // Display error message in UI if loading fails
            canvas_container.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: rgba(255,255,255,0.6); text-align: center; padding: 20px; font-size: 14px;">
                    <div>
                        <div style="font-size: 48px; margin-bottom: 10px;">⚠️</div>
                        <div style="margin-bottom: 10px;">Model Failed to Load</div>
                        <div style="font-size: 12px; opacity: 0.7; max-width: 250px;">${e.message}</div>
                        <div style="font-size: 11px; opacity: 0.5; margin-top: 10px;">Check console for details</div>
                    </div>
                </div>
            `;
        }
    })();
}

// === INTERACTION LOGIC ===
// Message interaction with audio AND motion
function messageInteraction(audio_link, motion){
    if(!model) {
        console.warn("Model not loaded yet");
        return;
    }
    
    // 1. Play Motion with High Priority
    if(motion) {
        console.log("🎬 Playing motion:", motion);
        // Priority 3 = FORCE (Forces motion to play, overrides idle/random motions)
        model.motion(motion, 0, 3); 
    }

    // 2. Play Audio using LipSync
    if(audio_link) {
        try {
            model.speak(audio_link, {
                volume: volume,
                expression: expression,
                resetExpression: resetExpression,
                crossOrigin: crossOrigin
            });
        } catch(e) {
            console.error("Audio playback error:", e);
        }
    }
}

// Event listeners for UI
btn.addEventListener('click', sendMessage);
input.addEventListener('keyup', function(e){ 
    if(e.keyCode == 13) sendMessage();
});

// Load Chat History
function loadHistory(){
    fetch('/history')
    .then(response => response.json())
    .then(data => {
        data.forEach(msg => {
            if (msg.role === 'user') {
                writeLine('USER', msg.content, 'primary');
            } else if (msg.role === 'assistant') {
                writeLine('Mei', msg.content, 'secondary');
            }
        });
    })
    .catch(error => console.error('Error loading history:', error));
}

loadHistory();

// Send Message Logic
function sendMessage(){
    const msg = input.value.trim();
    if(!msg) return;
    
    // Display user message immediately
    writeLine('USER', escapeHtml(msg), 'primary');
    input.value = '';
    
    // Disable input while processing to prevent spamming
    input.disabled = true;
    btn.disabled = true;
    btn.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';
    
    // Send to Backend
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 'message': msg })
    })
    .then(response => response.json())
    .then(data => {
        // Display AI response
        addMessage(data, 'secondary');
    })
    .catch(error => {
        console.error('Error:', error);
        writeLine('SYSTEM', 'Error: Could not send message', 'secondary');
    })
    .finally(() => {
        // Re-enable input
        input.disabled = false;
        btn.disabled = false;
        btn.textContent = 'Send';
        input.focus();
    });
}

// Add message to UI and Trigger Interaction
function addMessage(msg, typeMessage = 'primary'){
    writeLine(msg.FROM || 'Mei', msg.MESSAGE, typeMessage);
    // Send Audio AND Motion to interaction function
    if(msg.WAV) {
        messageInteraction(msg.WAV, msg.MOTION);
    }
}

// Write line with new UI structure (HTML generation)
function writeLine(sender, text, typeMessage){
    const message = document.createElement('li');
    message.classList.add('message-item', 'item-' + typeMessage);
    message.innerHTML = `
        <div class="message-avatar">${sender.charAt(0)}</div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="message-sender">${sender}</div>
                <div class="message-text">${text}</div>
            </div>
        </div>
    `;
    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight; // Auto-scroll to bottom
}

// HTML escape utility (Security: prevent XSS)
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-focus on input on load
input.focus();

// Welcome message after a short delay if chat is empty
setTimeout(() => {
    if(messages.children.length === 0) {
        writeLine('Mei', 
            '<div class="english-translation">Welcome! Is there anything I can help you with?</div><div class="japanese-response">ようこそ！何かお手伝いできることはありますか？</div>', 
            'secondary');
    }
}, 1000);

}