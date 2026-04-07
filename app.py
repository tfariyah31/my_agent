import os
import json
import streamlit as st
from groq import Groq
from ddgs import DDGS
import chromadb
from chromadb.utils import embedding_functions
from logger import log_decision, init_logger

# --- Setup ---
client = Groq(api_key=os.environ["GROQ_API_KEY"])
chroma_client = chromadb.PersistentClient(path="./agent_memory")
embedding_fn = embedding_functions.DefaultEmbeddingFunction()
collection = chroma_client.get_or_create_collection(
    name="agent_memory",
    embedding_function=embedding_fn
)

# --- Persistent Memory ---
class PersistentMemory:
    def save(self, role: str, content: str):
        doc_id = f"{role}_{collection.count()}"
        collection.add(
            documents=[content],
            metadatas=[{"role": role}],
            ids=[doc_id]
        )

    def recall(self, query: str, n=3) -> str:
        if collection.count() == 0:
            return ""
        try:
            results = collection.query(
                query_texts=[query],
                n_results=min(n, collection.count())
            )
            if not results["documents"][0]:
                return ""
            memories = []
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                role = meta.get("role", "unknown")
                if doc and len(doc.strip()) > 0 and len(doc) < 2000:
                    memories.append(f"{role.upper()}: {doc.strip()}")
            return "\n".join(memories)
        except Exception as e:
            print(f">>> memory.recall ERROR: {e}")
            return ""

memory = PersistentMemory()

# --- Tool ---
def web_search(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        return json.dumps([{"title": r["title"], "body": r["body"]} for r in results])
    except Exception as e:
        return f"Search error: {str(e)}"

# --- Agent ---
def run_agent(user_input: str, session_messages: list, status=None) -> str:
    print(f"\n>>> run_agent called with: {user_input}")
    init_logger()

    try:
        recalled = memory.recall(user_input)
        print(f">>> recalled: {recalled}")
    except Exception as e:
        print(f">>> memory.recall ERROR: {e}")
        recalled = ""

    memory_block = f"\nRelevant past memory:\n{recalled}" if recalled else ""
    if len(memory_block) > 3000:
        memory_block = memory_block[:3000] + "...(truncated)"

    system_prompt = (
    "You are a research assistant with persistent memory.\n"
    "You have access to a tool: web_search(query).\n"
    "RULES:\n"
    "- If the question is about current events, news, prices, or recent information: use web search\n"
    "- If the question is about a specific person, place, product, or company: use web search\n"
    "- If the question is something you discussed before in memory: answer from memory\n"
    "- If the question is simple general knowledge you are confident about: answer directly\n"
    "If you need to search, respond ONLY with: ACTION: web_search(\"your query\")\n"
    "If you can answer from memory or your own knowledge, respond ONLY with: ANSWER: [your response]\n"
    "NEVER respond in any other format. Always start with either ACTION: or ANSWER:\n"
    f"{memory_block}"
    )
    
    print(f"\n--- SYSTEM PROMPT ---\n{system_prompt}\n---")

    memory.save("user", user_input)
    messages = [{"role": "system", "content": system_prompt}] + session_messages

    for i in range(5):
        if status:
            status.info("Thinking...")

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0
            )
        except Exception as e:
            print(f">>> GROQ API ERROR: {e}")
            log_decision(user_input, i+1, "error", f"Groq API error: {str(e)}")
            return f"API error: {str(e)}"

        content = response.choices[0].message.content
        print(f"\n[Iteration {i+1}] LLM Output: {content}")

        if "ACTION: web_search(" in content:
            query = content.split('("')[1].split('")')[0]
            if status:
                status.warning(f"Searching the web for: _{query}_")
            print(f"--- Executing Search: {query} ---")
            log_decision(user_input, i+1, "search", f"Query: {query}")
            result = web_search(query)
            log_decision(user_input, i+1, "search_result", query, result[:500])
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": f"TOOL_RESULT: {result}\n\nNow summarize this and respond with ANSWER: [your summary]. Do not search again."
        })
        elif "ANSWER:" in content:
            answer = content.replace("ANSWER:", "").strip()
            log_decision(user_input, i+1, "answer", answer)
            memory.save("assistant", answer)
            return answer

        else:
            log_decision(user_input, i+1, "think", content)

    last = content.replace("ANSWER:", "").strip()
    
    return last if last else "I could not find an answer. Please try again."

# --- Streamlit UI ---
st.set_page_config(page_title="AI Agent", page_icon="🤖")
st.title("AI Research Agent")
st.caption("Powered by Groq + DuckDuckGo + ChromaDB")

tab1, tab2 = st.tabs(["Chat", "Decision Log"])

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.header("Memory")
    if st.button("Clear session"):
        st.session_state.messages = []
        st.success("Session cleared.")
    if st.button("Clear all memory"):
        chroma_client.delete_collection("agent_memory")
        collection = chroma_client.get_or_create_collection(
            name="agent_memory",
            embedding_function=embedding_fn
        )
        st.session_state.messages = []
        st.success("All memory wiped.")
    st.markdown("---")
    st.caption(f"Long-term memories stored: {collection.count()}")
    st.markdown("---")
    if st.button("Show memory"):
        if collection.count() == 0:
            st.info("No memories stored yet.")
        else:
            results = collection.get()
            for doc, meta in zip(results["documents"], results["metadatas"]):
                role = meta.get("role", "unknown")
                if role == "user":
                    st.chat_message("user").markdown(doc)
                else:
                    st.chat_message("assistant").markdown(doc)

# --- Tab 1: Chat ---
with tab1:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- Tab 2: Decision Log ---
with tab2:
    st.subheader("Decision log")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Refresh log"):
            pass
    with col2:
        if st.button("Clear log"):
            try:
                with open("logs/decisions.json", "w") as f:
                    json.dump([], f)
                st.success("Log cleared.")
            except FileNotFoundError:
                st.info("No log file yet.")

    try:
        with open("logs/decisions.json", "r") as f:
            logs = json.load(f)
        if not logs:
            st.info("No decisions logged yet.")
        else:
            seen = {}
            for entry in logs:
                q = entry["user_input"]
                if q not in seen:
                    seen[q] = "memory"
                if entry["action"] == "search":
                    seen[q] = "web search"

            st.markdown("### Summary")
            for question, source in reversed(list(seen.items())):
                icon = "🔍" if source == "web search" else "🧠"
                st.markdown(f"{icon} **{question}** → used **{source}**")

    except FileNotFoundError:
        st.info("No log file yet. Ask a question first.")
    
# --- Chat input OUTSIDE tabs so it stays fixed at bottom ---
if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with tab1:
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            status = st.empty()
            status.info("Thinking...")
            answer = run_agent(prompt, st.session_state.messages, status)
            status.empty()
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})