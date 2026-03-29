# Grok AI Interface

A clean, native local web interface for interacting with Grok AI via the `x.ai` API. This project provides a custom frontend and a Python backend designed specifically for Grok's native `v1/responses` endpoint, ensuring full compatibility with multi-agent capabilities that standard OpenAI wrappers often miss.

## Features

- **Built for Grok:** Uses the native `v1/responses` API endpoint for accurate Grok behavior.
- **Message-Based Context Limiter:** Control context length by the number of messages rather than tokens for a more intuitive experience.
- **Smart Image Handling:** Drag-and-drop or clipboard upload support, with a toggle to prevent resubmitting the same image on every message to save bandwidth and tokens.
- **Local Session Management:** Your chats are saved entirely locally as JSON files. No data is sent anywhere besides the official x.ai API.
- **Clean UI:** Simple, un-bloated settings panel and chat experience.

## Prerequisites

- Python 3.8 or higher
- An active `x.ai` API Key

## Setup & Installation

1. Clone or download this repository.
2. Install the required Python dependencies:

```bash
pip install fastapi uvicorn httpx pydantic
```

## How to Run

### On Windows
Simply double-click the `start_grok.bat` script. This will automatically start the backend server and open the web client (`index.html`) in your default browser.

### Manual Start (Any OS)
1. Start the backend server:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```
2. Open `index.html` in your web browser.

## Usage

1. Open the web interface.
2. Enter your Grok API key into the settings/input panel (it will be saved securely in your browser's local storage).
3. Start chatting! Your sessions will be saved automatically in the local `sessions/` folder.

## Privacy & Security

Your API key is never hardcoded. It is saved directly in your browser's `localStorage` and sent directly to your local Python backend, which then securely forwards it in the headers to `x.ai`. Your chat histories are strictly saved locally on your machine.
