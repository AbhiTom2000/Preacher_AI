🕊️ Preacher AI: Your Local AI-Powered Pastoral Companion

💡 Project Overview: AI for Social Impact

Preacher AI is a low-cost, highly accessible Retrieval-Augmented Generation (RAG) system designed to provide 24/7, scripture-grounded spiritual and pastoral guidance.

Originally built for cloud LLMs, this version has been optimized for Local Execution to ensure total privacy, zero API costs, and high-speed "small talk" interactions using Ollama and Llama 3.2.

By anchoring the LLM’s responses to verified biblical text stored in a FAISS semantic vector database, Preacher AI ensures theological reliability without the typical hallucinations or rate-limiting frustrations of cloud providers.

✨ Core Features

Feature

Description

Impact

📖 Scripture-Grounded

RAG pipeline retrieves Bible verses for every response

Prevents theological inaccuracies

🌍 Multi-Lingual

English + Hindi retrieval and conversation

Greater faith accessibility

🏠 100% Local LLM

Runs via Ollama (Llama 3.2) on your own hardware

Total privacy & zero usage costs

💬 Pastoral Small Talk

Optimized for precise, warm, and brief responses

Natural, non-robotic interactions

⚙️ Fast Architecture

FAISS + async FastAPI + WebSockets

Instant responses even on modest hardware

🏛️ System Architecture

Component

Tech Stack

Role

Frontend

React.js, Tailwind CSS, WebSockets

Chat UI & Real-time communication

Backend API

FastAPI, Python, Uvicorn

RAG Logic + WebSocket Management

LLM Engine

Ollama (Llama 3.2:3b)

Empathetic pastoral "small talk" generation

RAG/Search

FAISS + Sentence-Transformers

High-speed semantic scripture retrieval

Database

MongoDB + JSON Storage

Persistent chat history & Bible source data

⚙️ Setup & Installation

To run this application, you must start the Ollama service, the Backend API, and the Frontend App.

🧠 1️⃣ Local LLM Setup (Ollama)

Download and install Ollama from ollama.com.

Open your terminal and pull the optimized small-talk model:

ollama pull llama3.2:3b


🐍 2️⃣ Backend Setup (FastAPI)

Navigate to the backend/ directory.

Create a virtual environment: python -m venv venv.

Activate it:

Windows: .\venv\Scripts\activate

Mac/Linux: source venv/bin/activate

Install dependencies: pip install -r requirements.txt.

Configure your .env file:

MONGO_URL="your_mongodb_url"
DB_NAME="preacher_ai"
LLM_BASE_URL="http://localhost:11434/v1"
LLM_MODEL="llama3.2:3b"
LLM_API_KEY="ollama"


Start the server:

uvicorn server:app --reload


⚛️ 3️⃣ Frontend Setup (React)

Navigate to the frontend/ directory.

Install packages: npm install.

Start the UI: npm start.

🕊️ Pastoral Persona: "Small Talk" Logic

The AI is configured to be a "Preacher in your pocket." Unlike typical LLMs that give long essays, Preacher AI is restricted via system prompts to:

Respond in 3 sentences or less.

Maintain a warm, brief, and encouraging tone.

Avoid academic jargon in favor of spiritual warmth.

🤝 Contributing

We welcome contributions that improve the semantic search accuracy or add more Bible versions! 🌍

Fork the Project.

Create your Feature Branch (git checkout -b feature/AmazingFeature).

Commit your Changes (git commit -m 'Add amazing feature').

Push to the Branch (git push origin feature/AmazingFeature).

Open a Pull Request.

📜 License

Distributed under the MIT License. See LICENSE.txt for more information.