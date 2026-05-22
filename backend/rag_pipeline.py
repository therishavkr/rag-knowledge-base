from groq_service import get_llm
from vector_store import search_chunks
from langchain_core.messages import HumanMessage, SystemMessage

def ask_question(query: str, chat_history: list = [], collection_names: list = []) -> dict:
    # Step 1: Retrieve relevant chunks from selected collections
    relevant_chunks = search_chunks(query, collection_names, n_results=5)

    if not relevant_chunks:
        return {
            "answer": "I couldn't find any relevant information in the selected documents.",
            "sources": [],
            "chunks_used": 0
        }

    # Step 2: Build context
    context = "\n\n".join([chunk.page_content for chunk in relevant_chunks])

    # Step 3: Build messages
    messages = [
        SystemMessage(content=f"""You are a helpful assistant that answers questions based ONLY on the provided context.
If the answer is not in the context, say "I don't have enough information in the uploaded documents to answer this."

Context from documents:
{context}""")
    ]

    for turn in chat_history:
        messages.append(HumanMessage(content=turn["question"]))
        messages.append(SystemMessage(content=turn["answer"]))

    messages.append(HumanMessage(content=query))

    # Step 4: Send to Groq
    llm = get_llm()
    response = llm.invoke(messages)

    # Step 5: Collect sources
    sources = list(set([
        chunk.metadata.get("source", "Unknown")
        for chunk in relevant_chunks
    ]))

    return {
        "answer": response.content,
        "sources": sources,
        "chunks_used": len(relevant_chunks)
    }

def search_only(query: str, collection_names: list = []) -> dict:
    relevant_chunks = search_chunks(query, collection_names, n_results=5)

    if not relevant_chunks:
        return {
            "answer": "No relevant chunks found.",
            "sources": [],
            "chunks_used": 0
        }

    # Just return raw chunks, no LLM
    raw_results = "\n\n---\n\n".join([
        f"📄 {chunk.metadata.get('source', 'Unknown')} (page {chunk.metadata.get('page', '?')})\n{chunk.page_content}"
        for chunk in relevant_chunks
    ])

    sources = list(set([
        chunk.metadata.get("source", "Unknown")
        for chunk in relevant_chunks
    ]))

    return {
        "answer": raw_results,
        "sources": sources,
        "chunks_used": len(relevant_chunks)
    }