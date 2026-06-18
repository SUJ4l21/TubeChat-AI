from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os


from langchain_google_genai import GoogleGenerativeAIEmbeddings,ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from youtube_transcript_api import YouTubeTranscriptApi,TranscriptsDisabled
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import RunnableLambda,RunnableParallel,RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()
app = FastAPI(title='TubeChat RAG backend')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows extension contexts
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vector_stores = {}

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

#indexing( Embedding generation and vector store)
rate_limiter = InMemoryRateLimiter(
    requests_per_second=1.3333,  
    check_every_n_seconds=0.1,
    max_bucket_size=80 
)

embeddings = GoogleGenerativeAIEmbeddings(model='gemini-embedding-2-preview',rate_limiter=rate_limiter)
#Augmentation
llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash',temperature=0.2)
parser = StrOutputParser()
prompt = PromptTemplate(
    template="""
You are a smart, friendly assistant embedded in a YouTube video chat tool.
You have access to the transcript of the video the user is currently watching.

Your behavior depends on the type of question:

---

CASE 1 — Question is about the VIDEO:
- Answer strictly using the transcript context below.
- Be concise, natural, and conversational — not robotic.
- If the transcript doesn't cover it, say something like:
  "The video doesn't seem to cover that part, but here's what I found in it: ..."
- Never say a flat "I don't know" — always try to point to what IS available.

CASE 2 — Question is general / casual (not about the video):
- Answer like a knowledgeable, friendly human would.
- Do NOT restrict yourself to the transcript.
- Examples: greetings, follow-up questions, general curiosity, opinions, explanations of concepts mentioned in the video.
- Be warm, natural, and helpful — like a friend who also watched the video.

---

TRANSCRIPT CONTEXT:
{context}

---

CONVERSATION RULES:
- Never start a reply with "I don't know" as the full answer.
- Never say "the context is insufficient" — the user doesn't care about your internals.
- If unsure, make your best effort and be transparent naturally:
  ("I'm not 100% sure, but...", "Based on what I caught in the video...")
- Keep replies short and human unless the user asks for detail.
- Match the user's energy — casual question = casual reply, deep question = thorough reply.

---

Question: {question}
""",
    input_variables=['context','question']
    
)
 

def format_docs(retrieved_docs):
    context_text = "\n\n".join(doc.page_content for doc in retrieved_docs)
    return context_text


class InitializeRequest(BaseModel):
    video_id : str

class ChatRequest(BaseModel):
    video_id:str
    question : str
    
@app.post('/initialize')
async def initialize_video(payload: InitializeRequest):
    video_id = payload.video_id
    
    if video_id in vector_stores:
        return {'status':'ready' ,"message": "Video already indexed in cache."}
    
    try:
        
        proxy_url = os.getenv("PROXY_URL")
        
        # 2. Format it into the dictionary required by the API
        my_proxies = {
            "http": proxy_url,
            "https": proxy_url
        }

        ytt_api = YouTubeTranscriptApi()
        # Document Ingestion via Proxy
        transcript_data = ytt_api.fetch(
            video_id, 
            languages=['en'],
            proxies=my_proxies
        )
        
        transcript = ' '.join(chunk.text for chunk in transcript_data.snippets)
        
        # Text Splitting
        chunks = splitter.create_documents([transcript])
        
        # Vector Store Generation
        vector_store = FAISS.from_documents(chunks, embeddings)
        
        # Cache the vector store object using the unique video_id
        vector_stores[video_id] = vector_store
        
        print(f"Successfully cached FAISS index for video: {video_id}")
        return {"status": "ready", "message": "Video transcript successfully processed."}
    
    except TranscriptsDisabled:
        raise HTTPException(status_code=400, detail="No captions or transcripts are available for this video.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal pipeline failure: {str(e)}")
    
    
    
@app.post('/chat')
async def chat_with_video(payload: ChatRequest):
    video_id = payload.video_id
    question = payload.question
    
    vector_store = vector_stores.get(video_id)
    if not vector_store:
        raise HTTPException(
            status_code=404,
            detail='vector store content missing. Please initialize this video first.'
        )
    try:
        retriever = vector_store.as_retriever(search_type='similarity', search_kwargs={'k': 4})
        
        # Reconstruct your exact parallel execution chain
        parallel_chain = RunnableParallel({
            'context': retriever | RunnableLambda(format_docs),
            'question': RunnablePassthrough()
        })
        
        main_chain = parallel_chain | prompt | llm | parser
        
        # Execute chain query
        answer = main_chain.invoke(question)
        return {"answer": answer}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chain execution error: {str(e)}")
    
    
if __name__ == '__main__':
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)