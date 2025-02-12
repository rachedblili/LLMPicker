import streamlit as st
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.text_splitter import TokenTextSplitter
from uuid import uuid4
from datetime import datetime
from llama_index.core.types import ChatMessage, MessageRole
import llms

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

CONTEXT_SIZE = 65536

@dataclass
class Message:
    role: str
    content: str


@dataclass
class Conversation:
    id: str
    provider: Optional[str] = None
    model: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    client: Optional[SimpleChatEngine] = None
    memory: Optional[ChatMemoryBuffer] = None

    @property
    def is_initialized(self) -> bool:
        return self.provider is not None and self.model is not None


# Initialize session state
if "provider_model_hierarchy" not in st.session_state:
    st.session_state.provider_model_hierarchy = {
        provider: llms.list_models(provider)
        for provider in llms.list_providers()
    }
if "menu_state" not in st.session_state:
    st.session_state.menu_state = {
        "expanded_provider": None
    }
if "conversations" not in st.session_state:
    st.session_state.conversations: Dict[str, Conversation] = {}
if "active_conversation_id" not in st.session_state:
    st.session_state.active_conversation_id: Optional[str] = None


def render_hierarchical_menu():
    """Renders the hierarchical menu in the sidebar"""
    st.sidebar.markdown("### Select Model")

    # Style for the menu
    st.markdown("""
        <style>
        /* Only style buttons within the model selection menu */
        .element-container[class*="st-key-provider"] div[data-testid="stButton"],
        .element-container[class*="st-key-model"] div[data-testid="stButton"] {
            background: transparent;
            border: none;
            padding: 0;
        }
        
        /* Rest of the CSS remains the same but with more specific selectors */
        .element-container[class*="st-key-provider"] div[data-testid="stButton"] button,
        .element-container[class*="st-key-model"] div[data-testid="stButton"] button {
            display: flex;
            padding: 8px;
            margin: 2px 0;
            cursor: pointer;
            border-radius: 4px;
            background: transparent;
            border: none;
            width: 100%;
            box-shadow: none;
        }

        /* Provider-specific buttons */
        .element-container[class*="st-key-provider"] button[data-testid="stBaseButton-secondary"] {
            justify-content: flex-start !important;
        }
        .element-container[class*="st-key-provider"] div[data-testid="stMarkdownContainer"] {
            text-align: left !important;
        }
        .element-container[class*="st-key-provider"] div[data-testid="stMarkdownContainer"] p {
            text-align: left !important;
            font-weight: bold;
        }

        /* Model-specific buttons */
        .element-container[class*="st-key-model"] button[data-testid="stBaseButton-secondary"] {
            justify-content: center !important;
        }
        .element-container[class*="st-key-model"] div[data-testid="stMarkdownContainer"] {
            text-align: center !important;
        }
        .element-container[class*="st-key-model"] div[data-testid="stMarkdownContainer"] p {
            text-align: center !important;
            padding-left: 24px;
            font-size: 0.9em;
        }
        </style>
    """, unsafe_allow_html=True)

    # For each provider
    for provider in st.session_state.provider_model_hierarchy.keys():
        is_expanded = st.session_state.menu_state["expanded_provider"] == provider

        # Provider button with arrow and name
        arrow = "▼" if is_expanded else "▶"
        if st.sidebar.button(
                f"{arrow}&nbsp;&nbsp;&nbsp;&nbsp;{provider}",
                key=f"provider_{provider}",
                use_container_width=True,
        ):
            if is_expanded:
                st.session_state.menu_state["expanded_provider"] = None
            else:
                st.session_state.menu_state["expanded_provider"] = provider
            st.rerun()

        # If expanded, show models
        if is_expanded:
            for model in st.session_state.provider_model_hierarchy[provider]:
                if st.sidebar.button(
                        model,
                        key=f"model_{provider}_{model}",
                        use_container_width=True,
                ):
                    new_conv_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
                    st.session_state.conversations[new_conv_id] = Conversation(
                        id=new_conv_id,
                        provider=provider,
                        model=model
                    )
                    st.session_state.active_conversation_id = new_conv_id
                    st.session_state.menu_state["expanded_provider"] = None
                    st.rerun()


# Sidebar
st.sidebar.title("Conversations")

if not (st.session_state.active_conversation_id and
        not st.session_state.conversations[st.session_state.active_conversation_id].is_initialized):
    # New conversation button
    if st.sidebar.button("Start New Conversation"):
        new_conv_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
        st.session_state.conversations[new_conv_id] = Conversation(id=new_conv_id)
        st.session_state.active_conversation_id = new_conv_id
        st.rerun()

    # Show existing conversations
    if any(conv.is_initialized for conv in st.session_state.conversations.values()):
        st.sidebar.subheader("Existing Conversations")
        conv_options = {
            f"{conv.provider} - {conv.model} ({len(conv.messages)} messages)": conv_id
            for conv_id, conv in st.session_state.conversations.items()
            if conv.is_initialized
        }

        # Determine the label of the active conversation, if any
        active_conversation_index = 0
        if st.session_state.active_conversation_id:
            try:
                active_conversation_index = list(conv_options.values()).index(st.session_state.active_conversation_id)
            except ValueError:
                # Handle the case where the active_conversation_id is no longer in conv_options
                # This can happen if the conversation was deleted or somehow became invalid
                st.warning("Active conversation not found.  Resetting to the first conversation.")
                st.session_state.active_conversation_id = None  # Reset the active conversation
                if conv_options:
                    st.session_state.active_conversation_id = next(
                        iter(conv_options.values()))  # Set to first if available
                active_conversation_index = 0  # Reset index to 0

        selected = st.sidebar.radio(
            "Select Conversation",
            options=list(conv_options.keys()),
            index=active_conversation_index if conv_options else 0  # Ensure index is 0 if no options
        )

        if selected:
            st.session_state.active_conversation_id = conv_options[selected]

    # Clear conversation button
    if st.session_state.active_conversation_id and st.sidebar.button("Clear Current Conversation"):
        del st.session_state.conversations[st.session_state.active_conversation_id]
        st.session_state.active_conversation_id = None
        st.rerun()

else:
    # If we have an active conversation that's not fully initialized, show the hierarchical menu
    render_hierarchical_menu()

    # Keep the cancel button
    if st.sidebar.button("Cancel", type="primary"):
        del st.session_state.conversations[st.session_state.active_conversation_id]
        st.session_state.active_conversation_id = None
        st.rerun()


# Main chat interface
if st.session_state.active_conversation_id:
    conv = st.session_state.conversations[st.session_state.active_conversation_id]
    if conv.is_initialized:
        st.title(f"Chat with {conv.model}")
        # Display messages
        for msg in conv.messages:
            with st.chat_message(msg.role):
                st.markdown(msg.content)

        # Chat input with unique key
        if user_input := st.chat_input("Type your message...", key=f"chat_input_{conv.id}"):
            # Add user message
            conv.messages.append(Message(role="user", content=user_input))
            with st.chat_message("user"):
                st.markdown(user_input)

            try:
                # Initialize client if needed
                if conv.client is None:
                    client_fn = llms.client_functions[conv.provider]
                    conv.memory = ChatMemoryBuffer.from_defaults(token_limit=CONTEXT_SIZE)
                    conv.client = SimpleChatEngine.from_defaults(
                        llm=client_fn(conv.model),
                        memory=conv.memory
                    )

                # Split text into chunks and process
                text_splitter = TokenTextSplitter(chunk_size=2048, chunk_overlap=0)
                chunks = text_splitter.split_text(user_input)

                # Process all chunks except the last one into memory
                for chunk in chunks[:-1]:
                    conv.memory.put(ChatMessage(role=MessageRole.USER, content=chunk))

                # Get chat history and process final chunk
                chat_history = conv.memory.get()
                response = conv.client.chat(chunks[-1], chat_history=chat_history)

                # Display and store response
                with st.chat_message("assistant"):
                    st.markdown(response)
                conv.messages.append(Message(role="assistant", content=str(response)))
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.title("Configuring conversation...")
else:
    st.title("Start or select a conversation")



