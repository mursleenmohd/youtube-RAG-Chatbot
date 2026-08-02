import os
import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from pinecone import Pinecone
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

class YouTubeRAGEngine:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            streaming=True
        )
        
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "youtube-rag")
        self.index = self.pc.Index(self.index_name)

    def _extract_video_id(self, url: str) -> str:
        url = url.strip()
        if "watch?v=" in url:
            return url.split("watch?v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            return url.split("youtu.be/")[1].split("?")[0]
        return url

    def _generate_vector(self, text: str):
        # Generates deterministic 384-dimensional dense vectors
        import hashlib
        hash_bytes = hashlib.md5(text.encode('utf-8')).digest()
        vector = []
        for i in range(384):
            val = (hash_bytes[i % 16] - 128) / 128.0
            vector.append(round(val, 4))
        return vector

    def _fetch_transcript_safe(self, video_id: str):
        try:
            return YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e:
            print(f"Standard API fetch error: {e}")

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
            print(f"Fallback Piped API fetch error: {e}")

        return []

    def process_video(self, video_url: str):
        video_id = self._extract_video_id(video_url)

        try:
            stats = self.index.describe_index_stats()
            if stats.get('namespaces') and video_id in stats['namespaces']:
                print(f"Video {video_id} already exists in Pinecone Cloud!")
                return True
        except Exception as e:
            print(f"Pinecone stats check warning: {str(e)}")

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

        vectors = []
        for i, doc in enumerate(docs):
            emb = self._generate_vector(doc.page_content)
            vectors.append({
                "id": f"{video_id}_{i}",
                "values": emb,
                "metadata": {"text": doc.page_content}
            })

        batch_size = 50
        for i in range(0, len(vectors), batch_size):
            self.index.upsert(vectors=vectors[i:i + batch_size], namespace=video_id)

        print(f"Successfully processed and uploaded vectors for: {video_id}")
        return True

    def stream_answer(self, video_id: str, question: str):
        q_emb = self._generate_vector(question)
        
        res = self.index.query(
            vector=q_emb,
            top_k=5,
            include_metadata=True,
            namespace=video_id
        )

        matched_texts = [match['metadata']['text'] for match in res.get('matches', []) if match.get('metadata')]
        context = "\n\n".join(matched_texts) if matched_texts else "No specific context available."

        prompt_template = """You are an AI assistant answering questions based on a YouTube video transcript.
Answer the question accurately using ONLY the context provided below.

IMPORTANT INSTRUCTION FOR TIMESTAMPS:
Whenever you extract information, always mention the relevant timestamp in the exact format `[MM:SS]` (e.g., [01:23] or [08:14]) where the discussion occurs in the transcript.

Context:
{context}

Question: {question}

Answer:"""

        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm | StrOutputParser()

        for chunk in chain.stream({"context": context, "question": question}):
            yield chunk