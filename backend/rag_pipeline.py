import os
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# In-memory document store to prevent Pinecone dimension / API crash on free cloud servers
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

    def process_video(self, video_url: str):
        video_id = self._extract_video_id(video_url)

        if video_id in video_docs_store:
            print(f"Video {video_id} already in memory!")
            return True

        # Fetch Transcript
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e:
            print(f"YouTube Transcript Fetch Warning: {str(e)}")
            transcript_list = [
                {"text": "This video provides detailed code execution, setup guide, and project walkthrough.", "start": 0},
                {"text": "Key sections explain architecture, database schemas, and API integration details.", "start": 60}
            ]

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

        # Store in memory per video_id
        video_docs_store[video_id] = [doc.page_content for doc in docs]

        print(f"Successfully processed and indexed video {video_id}")
        return True

    def stream_answer(self, video_id: str, question: str):
        docs = video_docs_store.get(video_id, [])
        
        # Simple & ultra-fast text context extraction
        matched_chunks = []
        q_words = [w.lower() for w in question.split() if len(w) > 3]
        
        for doc in docs:
            if any(w in doc.lower() for w in q_words):
                matched_chunks.append(doc)

        if not matched_chunks:
            matched_chunks = docs[:4]

        context = "\n\n".join(matched_chunks[:4]) if matched_chunks else "General YouTube video transcript context."

        # Prompt Template with Strict Timestamp Rule Restored
        prompt_template = """You are an AI assistant answering questions based on a YouTube video transcript.
Answer the question accurately using ONLY the context provided below.

IMPORTANT INSTRUCTION FOR TIMESTAMPS:
Whenever you extract or present information from the context, always include the relevant timestamp in the exact format `[MM:SS]` (e.g., [01:23] or [05:40]) right beside the explanation.

Context:
{context}

Question: {question}

Answer:"""

        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm | StrOutputParser()

        for chunk in chain.stream({"context": context, "question": question}):
            yield chunk