# app/services/summarization_service.py
import json

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig
from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.schemas.state import State
from app.services.youtube_service import search_youtube_video, get_youtube_transcript
from app.services.tts_service import text_to_speech
from app.config import MODEL_NAME, TOGETHER_API_KEY


# Initialize the LLM instance.
llm = init_chat_model( 
    model=MODEL_NAME, 
    model_provider="together",
    temperature=0.4,
    api_key=TOGETHER_API_KEY,
)

# Create the list of tools and bind them.
tools = [search_youtube_video, get_youtube_transcript]
tool_node = ToolNode(tools)
llm_with_tools = llm.bind_tools(tools)

# Define summarization prompts and chains.
summarize_prompt = ChatPromptTemplate(
    [
        (
            "human",
            """You are an AI assistant summarizing a YouTube video for someone who cannot watch it. 
            
            **Objective**: Provide a well-structured, engaging, and detailed summary based on the given transcript chunk.
            
            - Capture the **key points, themes, and emotions**.
            - If it's a **story-driven video** (e.g., movies, vlogs), enhance descriptions of **plot developments and twists, character actions, emotional moments, motivations, plot setting, location, time**
            - If it's **educational or informational**, focus on the **main insights, lessons, and takeaways**.
            - Keep it **concise yet descriptive**, making the user feel like they watched the video.
            - Don't mention "transcript" in the summary. Use a narrative tone as if you were Chimamanda Adichie or Morgan Freeman.
            - Use gendered pronouns (he/she) based on the video's content. Try to infer the gender from the context.
            
            Here is the first transcript segment:
            ----------------
            {context}
            ----------------
            
            Write a concise but detailed summary based on this content.
            """,
        )
    ]
)

initial_summary_chain = summarize_prompt | llm_with_tools | StrOutputParser()


refine_template = """
You are refining a summary of a YouTube video to make it **engaging, structured, and easy to understand**.

**Objective**: Merge the new context into the existing summary to create a refined version that truly reflects the video’s content.

### **Guidelines:**
- Maintain coherence and flow between the **existing summary** and **new context**.
- If the new content **introduces key moments**, ensure they are **properly included**.
- If it's a **story-driven video**, enhance descriptions of **plot developments, character actions, emotional moments, plot setting, location, time**.
- If it’s **informational**, refine the summary to **better capture main ideas and lessons**.
- Keep the summary **concise but engaging**, as if the user has watched the video.
- Don't mention "transcript" in the summary. Use a narrative tone as if you were Chimamanda Adichie or Morgan Freeman.
- Use gendered pronouns (he/she) based on the video's content. Try to infer the gender from the context.

---

### **Existing summary up to this point:**
{existing_answer}

### **New transcript segment:**
{context}

---

Now, refine the original summary, ensuring the **final version is coherent, engaging, and informative**.
"""

refine_prompt = ChatPromptTemplate([("human", refine_template)])

refine_summary_chain = refine_prompt | llm_with_tools | StrOutputParser()


# Workflow node functions.
def chunk_transcript(state: State, config: RunnableConfig, chunk_size: int = 60000):
    """
    Split the transcript into manageable chunks.
    """
    transcript = state.get("transcript")
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=500)
    transcript_chunks = splitter.split_text(transcript)
    return {"contents": transcript_chunks}

async def generate_initial_summary(state: State, config: RunnableConfig):
    summary = await initial_summary_chain.ainvoke(
        {"context": state["contents"][0]}, 
        config
    )
    return {"summary": summary, "index": 1}

async def refine_summary(state: State, config: RunnableConfig):
    content = state["contents"][state["index"]]
    summary = await refine_summary_chain.ainvoke(
        {"existing_answer": state["summary"], "context": content}, 
        config
    )
    return {"summary": summary, "index": state["index"] + 1}

def should_refine(state: State) -> str:
    if state["index"] >= len(state["contents"]):
        return END
    else:
        return "refine_summary"

def call_model(state: State):
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def should_continue(state: State) -> str:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls: # type: ignore
        return "tools"
    elif state.get("transcript") and not state.get("contents"):
        return "chunk_transcript"
    return END

# Build the workflow graph.
# --- Graph Arrangement ---

graph = StateGraph(State)

# Tool-calling part: to sequentially invoke the YouTube tools if needed.
# Add nodes.
graph.add_node("agent", call_model)
graph.add_node("tools", tool_node)
graph.add_node("chunk_transcript", chunk_transcript)
graph.add_node("generate_initial_summary", generate_initial_summary)
graph.add_node("refine_summary", refine_summary)

# Arrange edges for the tool-calling phase.
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue, {
    "tools": "tools",                     # If tool calls exist.
    "chunk_transcript": "chunk_transcript",  # If the transcript is available.
    END: END                              # Otherwise, end the workflow.
})
graph.add_edge("tools", "agent")  # After executing tools, return to the agent.

# After creating chunks of the transcript, start iterative summarization 
# beginning with the first chunk
graph.add_edge("chunk_transcript", "generate_initial_summary")
# Arrange edges for the summarization phase. 
graph.add_conditional_edges("generate_initial_summary", should_refine, {
    "refine_summary": "refine_summary",
    END: END
})
graph.add_conditional_edges("refine_summary", should_refine, {
    "refine_summary": "refine_summary",
    END: END
})

# Compile the graph.
app = graph.compile()

# Function that invokes the workflow with a query.
async def summarize_video(query: str, tts: bool = False) -> dict:
    final_state = None
    async for chunk in app.astream(
        {"messages": [("user", query)]},
        {"recursion_limit": 50},
        stream_mode="values"
    ):
        final_state = chunk

    summary = final_state.get("summary", "") if final_state else ""
    video_link = None
    title = None

    if final_state:
        for message in final_state.get("messages", []):
            if getattr(message, "name", None) == "search_youtube_video":
                try:
                    payload = json.loads(message.content)
                    video_link = payload.get("link")
                    title = payload.get("title")
                    break
                except json.JSONDecodeError:
                    continue

    audio_url = None
    if tts and summary:
        audio_path = text_to_speech(summary)
        audio_url = f"/{audio_path}"  # Assuming FastAPI serves static files from the 'assets' directory

    return {"title": title, "summary": summary, "video_link": video_link, "audio_url": audio_url}

