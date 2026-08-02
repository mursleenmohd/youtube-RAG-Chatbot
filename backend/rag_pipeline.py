import os
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from pinecone import Pinecone
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

class YouTubeRAGEngine:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            streaming=True
        )
        
        # Initialize Native Pinecone Client
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

    def process_video(self, video_url: str):
        video_id = self._extract_video_id(video_url)

        # Check if namespace already exists in Pinecone
        stats = self.index.describe_index_stats()
        if stats.get('namespaces') and video_id in stats['namespaces']:
            print(f"Video {video_id} already indexed in Pinecone Cloud!")
            return True

        # Fetch Transcript
        try:
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.fetch(video_id)
        except AttributeError:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        except (TranscriptsDisabled, NoTranscriptFound):
            raise ValueError("Subtitles/captions are disabled for this video.")

        formatted_chunks = []
        for item in transcript_list:
            text = item['text'] if isinstance(item, dict) else item.text
            start_sec = int(item['start'] if isinstance(item, dict) else item.start)
            
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

        # Generate Embeddings & Upsert directly to Pinecone Index
        vectors = []
        for i, doc in enumerate(docs):
            emb = self.embeddings.embed_query(doc.page_content)
            vectors.append({
                "id": f"{video_id}_{i}",
                "values": emb,
                "metadata": {"text": doc.page_content}
            })

        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            self.index.upsert(vectors=vectors[i:i + batch_size], namespace=video_id)

        print(f"Successfully uploaded vectors to Pinecone Cloud for namespace: {video_id}")
        return True

    def stream_answer(self, video_id: str, question: str):
        # Embed question & Query Pinecone Cloud
        q_emb = self.embeddings.embed_query(question)
        res = self.index.query(
            vector=q_emb,
            top_k=4,
            include_metadata=True,
            namespace=video_id
        )

        matched_texts = [match['metadata']['text'] for match in res.get('matches', [])]
        context = "\n\n".join(matched_texts)

        prompt_template = """You are an AI assistant answering questions based on a YouTube video transcript.
Answer the question accurately using ONLY the context provided below.

IMPORTANT INSTRUCTION FOR TIMESTAMPS:
Whenever you extract information, always mention the timestamp in the format `[MM:SS]` where the information occurs in the transcript.

Context:
{context}

Question: {question}

Answer:"""

        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm | StrOutputParser()

        # Stream Token-by-Token
        for chunk in chain.stream({"context": context, "question": question}):
            yield chunk