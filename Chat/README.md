# TubeChat

TubeChat is a local YouTube transcript chat tool that lets you ask questions about the currently open YouTube video using a browser extension UI and a Python backend.

## Architecture

The project is built as two main parts:

1. **FastAPI backend** (`backend/app.py`)
   - Uses `youtube-transcript-api` to fetch the transcript for a YouTube video.
   - Splits the transcript into chunks using `RecursiveCharacterTextSplitter`.
   - Converts transcript chunks into embeddings using `GoogleGenerativeAIEmbeddings`.
   - Stores those embeddings in a FAISS vector index.
   - Exposes two endpoints:
     - `POST /initialize` — fetches and indexes the transcript for a video ID.
     - `POST /chat` — retrieves similar transcript chunks and generates an AI answer.
   - Uses a Gemini chat model (`ChatGoogleGenerativeAI`) and a prompt template to answer questions.

2. **Browser extension UI** (`extension/`)
   - `manifest.json` defines a Chrome extension popup.
   - `popup.html` provides a minimal chat interface.
   - `popup.js` extracts the active YouTube video ID and communicates with the backend.
   - The popup sends the video ID to `/initialize`, then sends user questions to `/chat`.

### Data flow

1. User opens a YouTube video in the browser.
2. The extension popup reads the video URL and extracts the `v` parameter.
3. The popup calls the backend `/initialize` endpoint with that video ID.
4. The backend downloads the transcript, splits it, embeds it, and stores it in memory using FAISS.
5. When the user asks a question, the popup sends the question and video ID to `/chat`.
6. The backend retrieves the most relevant transcript chunks and queries the Gemini model.
7. The model returns a concise answer, which is displayed in the popup.

## Features

- Local YouTube video chat interface.
- Transcript retrieval and indexing on demand.
- Semantic search over transcript chunks.
- AI-generated answers based on the video transcript.
- Minimal browser extension UI for easy local use.

## Requirements

The project depends on:

- Python 3.14+ (local environment in `tubechat/` appears configured for Python 3.14)
- FastAPI
- Uvicorn
- python-dotenv
- langchain-google-genai
- langchain-core
- langchain-community
- langchain-text-splitters
- youtube-transcript-api
- faiss-cpu
- pydantic

These are listed in `requirements.txt`.

## Local setup

Follow these steps to run TubeChat locally on your PC.

### 1. Create and activate the Python environment

If you are not already using the provided `tubechat` virtual environment, create or activate a Python venv.

On Windows (PowerShell):

```powershell
python -m venv venv
.\
venv\Scripts\Activate.ps1
```

Or use the existing environment if it is already set up.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the backend server

From the project root:

```bash
python backend/app.py
```

This starts the FastAPI server on `http://127.0.0.1:5000`.

### 4. Load the extension in Chrome

1. Open Chrome and go to `chrome://extensions/`.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select the `extension/` folder inside the project.
5. The extension named `TubeChat AI` should appear.

### 5. Use TubeChat

1. Open a YouTube video page in Chrome.
2. Click the TubeChat extension icon.
3. Wait for the popup to finish initializing the video transcript.
4. Ask a question in the input field and press **Run**.
5. The backend will use the transcript and Gemini model to answer.

## Troubleshooting

- If the extension says the video ID is missing, make sure you are on a YouTube video page and that the URL contains `?v=`.
- If the backend returns an error, check the terminal running `backend/app.py` for details.
- If transcripts are unavailable for the video, the backend will return a `TranscriptsDisabled` error.

## Notes

- The vector store is cached in memory while the backend is running. If you restart the backend, the transcript index is rebuilt on the next video initialization.
- This project is intended for local use and development, not for production deployment.
