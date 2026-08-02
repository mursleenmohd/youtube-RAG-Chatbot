import os
import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

video_docs_store = {}

class YouTubeRAGEngine:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            streaming=True
        )

    def _extract_video_id(self, url: str) -> str:
        url = url.strip()
        if "watch?v=" in url:
            return url.split("watch?v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            return url.split("youtu.be/")[1].split("?")[0]
        return url

    def _fetch_transcript_safe(self, video_id: str):
        # 1. Try standard transcript
        try:
            return YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e:
            print(f"Standard API failed: {e}")

        # 2. Try third-party transcript API fallback (Free Supadata/Piped API)
        try:
            res = requests.get(f"https://pipedapi.kavin.rocks/subtitles/{video_id}?lang=en", timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data and len(data) > 0:
                    sub_url = data[0]['url']
                    sub_res = requests.get(sub_url, timeout=10).json()
                    formatted = []
                    for item in sub_res:
                        formatted.append({
                            "text": item.get("text", ""),
                            "start": item.get("start", 0)
                        })
                    return formatted
        except Exception as e:
            print(f"Fallback Piped API failed: {e}")

        # Return empty list if no transcript found
        return []

    def process_video(self, video_url: str):
        video_id = self._extract_video_id(video_url)

        if video_id in video_docs_store:
            return True

        transcript_list = self._fetch_transcript_safe(video_id)

        if not transcript_list:
            raise ValueError("Captions/Subtitles are unavailable or disabled for this video.")

        formatted_chunks = []
        for item in transcript_list:
            text = item['text'] if isinstance(item, dict) else getattr(item, 'text', '')
            start_sec = int(item['start'] if isinstance(item, dict) else getattr(item, 'start', 0))
            
            minutes = start_sec // 60
            seconds = start_sec % 60
            time_str = f"[{minutes:02d}:{seconds:02d}]"
            
            formatted_chunks.append(f"{time_str} {text}")

        full_text = "\n".join(formatted_chunks)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150
        )
        docs = text_splitter.create_documents([full_text])
        video_docs_store[video_id] = [doc.page_content for doc in docs]
        return True

    def stream_answer(self, video_id: str, question: str):
        docs = video_docs_store.get(video_id, [])
        
        matched_chunks = []
        q_words = [w.lower() for w in question.split() if len(w) > 3]
        
        for doc in docs:
            if any(w in doc.lower() for w in q_words):
                matched_chunks.append(doc)

        if not matched_chunks:
            matched_chunks = docs[:4]

        context = "\n\n".join(matched_chunks[:4]) if matched_chunks else "No relevant context found."

        prompt_template = """You are an AI assistant answering questions based on a YouTube video transcript.
Answer the question accurately using ONLY the context provided below.

IMPORTANT INSTRUCTION FOR TIMESTAMPS:
Whenever you extract information, always mention the relevant timestamp in format `[MM:SS]` (e.g. [01:23]).

Context:
{context}

Question: {question}

Answer:"""

        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm | StrOutputParser()

        for chunk in chain.stream({"context": context, "question": question}):
            yield chunk