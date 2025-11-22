# 🕊️ Preacher AI: Your AI-Powered Pastoral Companion

## 💡 Project Overview: AI for Social Impact

**Preacher AI** is a low-cost, highly accessible **Retrieval-Augmented Generation (RAG)** system designed to provide **24/7, scripture-grounded spiritual and pastoral guidance**.

It addresses key community challenges:
- Limited access to emotional/spiritual support
- Language barriers in theological understanding
- AI model hallucinations in religious contexts

By anchoring Gemini LLM’s responses to **verified biblical text** stored in a **FAISS semantic vector database**, Preacher AI ensures **theological reliability** while keeping **operational costs minimal**.

---

## ✨ Core Features

| Feature | Description | Impact |
|--------|-------------|--------|
| 📖 Scripture-Grounded Responses | RAG pipeline retrieves Bible verses for every response | Prevents theological inaccuracies |
| 🌍 Multi-Lingual Support | English + Hindi retrieval and conversation | Greater faith accessibility |
| ⚙️ Low-Cost Architecture | FAISS + async FastAPI + WebSockets | High scalability at minimal cost |
| 📌 24/7 Emotional Support | Empathetic pastoral guidance | Mental & emotional well-being |

---

## ⚙️ Setup & Available Scripts

To run this application, start **both** the Backend API (FastAPI) and the Frontend App (React).

---

### 🧠 1️⃣ Backend Setup (FastAPI RAG Server)

This handles the RAG engine + real-time WebSocket chat.

#### Prerequisites
- Python 3.10+
- Gemini API Key (environment variable)

```bash
cd backend
pip install -r requirements.txt
```

#### Set Gemini key:

```bash
export GEMINI_API_KEY="YOUR_API_KEY_HERE"
```

#### Run server:

```bash
uvicorn server:app --reload --ws-max-size 10000000
```

Backend available at:
➡️ **http://127.0.0.1:8000**

---

### 💬 2️⃣ Frontend Setup (React Chat UI)

```bash
cd frontend
npm install
npm start
```

Frontend available at:
➡️ **http://localhost:3000**

> Backend must be running FIRST ⚡

---

## 🏛️ System Architecture

| Component | Tech Stack | Role | Social Impact Alignment |
|----------|------------|------|-----------------------|
| Frontend | React.js, Tailwind CSS, WebSockets | Chat UI | Mobile-first + Low bandwidth use |
| Backend API | FastAPI, Python, Uvicorn | RAG + Real-time WS | Low cost + High concurrency |
| LLM | Google Gemini | Empathetic pastor-like responses | Emotional/Spiritual well-being |
| RAG/Search | FAISS + Sentence-Transformers | Scripture retrieval | Trustworthy biblical grounding |
| Data Storage | JSON + FAISS Index | Bible data & embeddings | English + Hindi accessibility |

---

## 📦 Repository Structure

```
preacher_ai/
├── backend/                  # RAG Engine (FastAPI)
│   ├── storage/              # Bible text + vector index
│   │   ├── english_bible_verses.json
│   │   └── faiss/
│   ├── requirements.txt
│   └── server.py
└── frontend/                 # React UI
    ├── public/
    ├── src/
    │   ├── App.js
    │   └── assets/           # logo + backgrounds
    └── package.json
```

---

## 🤝 Contributing

We welcome all contributions! 🌍

```bash
git checkout -b feature/AmazingFeature
# implement your idea 🎯
git commit -m "Add amazing feature"
git push origin feature/AmazingFeature
```

Then create a Pull Request 🙌

---

## 📜 License

This project is licensed under the **MIT License**.  

---

🚀 *Preacher AI: Empowering Bible through technology.*
