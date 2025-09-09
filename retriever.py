import os
from typing import List
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
load_dotenv()


class EventHubRetriever:
    def __init__(self, collection_name="documents", db_path="data/chroma_db"):
        """Initialize retriever with ChromaDB + Gemini embeddings"""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        # Set up Gemini embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004"
        )

        # Connect to existing Chroma collection (persisted)
        self.vectorstore = Chroma(
            collection_name=collection_name,
            persist_directory=db_path,
            embedding_function=self.embeddings,
        )

        # Expose a retriever interface
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})

    def retrieve_context(self, query: str, n_results: int = 3) -> List[str]:
        """Retrieve relevant context documents for query"""
        try:
            docs = self.vectorstore.similarity_search(query, k=n_results)
            return [doc.page_content for doc in docs]
        except Exception as e:
            print(f"Retrieval error: {e}")
            return []

    def format_context(self, documents: List[str]) -> str:
        """Format retrieved documents into context string"""
        if not documents:
            return "No relevant context found."

        context = "Relevant information:\n"
        for i, doc in enumerate(documents, 1):
            context += f"{i}. {doc.strip()}\n"

        return context.strip()

    def get_formatted_context(self, query: str, n_results: int = 3) -> str:
        """Get and format context in one call"""
        documents = self.retrieve_context(query, n_results)
        return self.format_context(documents)


if __name__ == "__main__":
    retriever = EventHubRetriever()
    context = retriever.get_formatted_context("What events are happening?")
    print(context)
