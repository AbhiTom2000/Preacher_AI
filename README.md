# 🕊️ Preacher AI: Your Local AI-Powered Pastoral Companion

## 💡 Project Overview: AI for Social Impact

**Preacher AI** is a low-cost, highly accessible **Retrieval-Augmented Generation (RAG)** system designed to provide **24/7, scripture-grounded spiritual and pastoral guidance**.

It addresses key community challenges:

- Limited access to emotional/spiritual support  
- Language barriers in theological understanding  
- AI model hallucinations in religious contexts  

By anchoring the LLM’s responses to **verified biblical text** stored in a **FAISS semantic vector database**, Preacher AI ensures **theological reliability** while keeping **operational costs zero** by running entirely on your local hardware.

---

## ✨ Core Features

| Feature | Description | Impact |
|--------|-------------|--------|
| 📖 Scripture-Grounded | RAG pipeline retrieves Bible verses for every response | Prevents theological inaccuracies |
| 🌍 Multi-Lingual Support | English + Hindi retrieval and conversation | Greater faith accessibility |
| 🏠 100% Local LLM | Runs via Ollama (Llama 3.2) on your own hardware | Total privacy & zero usage costs |
| 💬 Pastoral Small Talk | Optimized for precise, warm, and brief responses | Natural, non-robotic interactions |
| ⚙️ Fast Architecture | FAISS + async FastAPI + WebSockets | Instant responses on modest hardware |

---

## ⚙️ Setup & Available Scripts

To run this application, start both the **Backend API (FastAPI)** and the **Frontend App (React)**.

---

## 🧠 1️⃣ Local LLM Setup (Ollama)

Download and install Ollama: https://ollama.com

```bash
ollama pull llama3.2:3b
```

---

## 🐍 2️⃣ Backend Setup

```bash
cd backend
python -m venv venv
```

Activate environment:

Windows:
```bash
.\venv\Scripts\activate
```

Mac/Linux:
```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Environment

```env
MONGO_URL="your_mongodb_url"
DB_NAME="preacher_ai"
LLM_BASE_URL="http://localhost:11434/v1"
LLM_MODEL="llama3.2:3b"
LLM_API_KEY="ollama"
```

### Run backend

```bash
uvicorn server:app --reload --ws-max-size 10000000
```

---

## 💬 3️⃣ Frontend Setup

```bash
cd frontend
npm install
npm start
```

---

## 🏛️ Architecture

- React Frontend
- FastAPI Backend
- Ollama Local LLM
- FAISS Vector Search
- JSON Bible Storage

---

## 📦 Structure

```
preacher_ai/
├── backend/
│   ├── storage/
│   ├── requirements.txt
│   └── server.py
└── frontend/
    ├── src/
    └── package.json
```

---

## 🤝 Contributing

```bash
git checkout -b feature/AmazingFeature
git commit -m "Add feature"
git push origin feature/AmazingFeature
```

---

## 📜 License

MIT License

---

🚀 *Preacher AI: Empowering faith through technology.*
