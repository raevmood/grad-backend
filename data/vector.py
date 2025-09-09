import os
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv
load_dotenv()


def load_txt_to_chroma(txt_file_path, collection_name="documents", persist_dir="./chroma_db"):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("❌ GOOGLE_API_KEY not set in environment variables")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    with open(txt_file_path, "r", encoding="utf-8") as f:
        text = f.read()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,  
        separators=["\n\n", "\n", ".", "!", "?", " ", ""]
    )
    docs = splitter.create_documents([text])

    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name=collection_name
    )

    print(f"✅ Added {len(docs)} chunks to collection '{collection_name}'")
    return vectorstore


if __name__ == "__main__":
    try:
        vectorstore = load_txt_to_chroma("Context.txt")

        query = "How do I submit an event"
        results = vectorstore.similarity_search(query, k=3)

        print("\n🔍 Search results:")
        for i, doc in enumerate(results, 1):
            print(f"{i}. {doc.page_content[:100]}...")

    except Exception as e:
        print(f"❌ Error: {e}")