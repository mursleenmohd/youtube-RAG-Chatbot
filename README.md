# YouTube Interactive RAG Chatbot

An end-to-end full-stack AI application that enables users to interactively chat with any YouTube video in real time. Built using **Retrieval-Augmented Generation (RAG)**, this tool extracts video transcripts, stores vector representations in the cloud, and streams accurate AI answers embedded with **clickable timestamps** that sync directly with the embedded YouTube player.

---

## Screenshots & Demo
<img width="1919" height="969" alt="image" src="https://github.com/user-attachments/assets/e3b71bff-9ed5-424d-8800-e6b1d8996359" />

|Forget Password|
<img width="1919" height="967" alt="image" src="https://github.com/user-attachments/assets/e31e20f5-b7bf-4a47-8792-288dcd5859c7" />


| Dashboard & Video RAG Interface | Real-time Streaming Chat |

<img width="1908" height="974" alt="image" src="https://github.com/user-attachments/assets/e02030d7-1e20-4c3b-8f30-8e3581358c72" />


## Key Features

- **User Authentication & Session Management**: Secure Sign Up, Login, and Password Reset (OTP via Brevo) powered by JWT.
- **Real-Time Streaming Responses**: Token-by-token LLM output streaming using Groq (Llama-3.3-70b).
- **Clickable Video Timestamps**: Extracted answers include `[MM:SS]` formatted timestamps that automatically seek the YouTube video player when clicked.
- **Hybrid Transcript Retrieval**: Multi-tier fallback system (Standard API + Proxy) to reliably fetch video subtitles even on cloud environments.
- **Persistent Vector Indexing**: Video embeddings are stored and retrieved efficiently using Pinecone Cloud Vector Database.
- **Modern Glassmorphism UI**: Responsive React frontend with active video session history and intuitive chat panels.

---

## Repository Directory Structure

```text
youtube-RAG-Chatbot/
├── backend/
│   ├── app.py                   # Main Flask Application & API Routes
│   ├── rag_pipeline.py          # RAG Engine (LangChain, Groq, Pinecone Pipeline)
│   ├── auth.py                  # JWT Auth & Email OTP Logic
│   ├── db.py                    # MySQL Database Connections
│   ├── requirements.txt         # Python Dependencies
│   └── .env.example             # Backend Environment Variables Example
│
├── frontend/
│   ├── src/
│   │   ├── components/          # Modular React Components
│   │   ├── App.jsx              # Main App Interface & Video Player Integration
│   │   ├── Auth.jsx             # Authentication UI Components
│   │   ├── App.css              # Custom Styling (Glassmorphism & Layouts)
│   │   └── main.jsx             # React Application Entry Point
│   ├── public/                  # Static Assets & Icons
│   ├── package.json             # Frontend Dependencies & Scripts
│   ├── vite.config.js           # Vite Configuration
│   └── .env.example             # Frontend Environment Variables Example
│
└── README.md                    # Project Documentation
