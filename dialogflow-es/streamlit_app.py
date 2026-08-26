"""
HoopMind - custom chat UI (Streamlit).

Run:
    python webhook.py            # terminal 1
    python -m streamlit run streamlit_app.py   # terminal 2
"""

import requests

import streamlit as st

CHAT_URL = "http://localhost:5000/chat"

st.set_page_config(page_title="HoopMind", page_icon="🏀", layout="centered")

st.markdown(
    """
    <style>
      .stChatMessage { border-radius: 14px; }
      div[data-testid='stChatMessage'] p { font-size: 0.95rem; }
      .hoop-card {
          background: rgba(120,120,140,0.10);
          border: 1px solid rgba(130,130,160,0.25);
          border-radius: 12px;
          padding: 14px 18px;
          margin-bottom: 4px;
      }
      .hoop-title {
          font-weight: 700; font-size: 1.02rem;
          margin-bottom: 2px;
      }
      .hoop-sub { color: #9aa3b2; font-size: 0.85rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

EXAMPLES = [
    "Tell me about LeBron James",
    "What were Stephen Curry's stats in 2016?",
    "What was Nikola Jokic's PER in 2023?",
    "Compare Kobe and Jordan career points",
    "Compare Boston Celtics and Miami Heat in 2024",
    "Who won MVP in 2016?",
    "Was Dirk an All-Star in 2010?",
    "Who was the first overall pick in 2003?",
]


def render_card(card: dict) -> None:
    ctype = card.get("type")

    if ctype == "info":

        st.markdown(
            "<div class='hoop-card'>"
            f"<div class='hoop-title'>"
            f"{card.get('title', '')}</div>"
            f"<div class='hoop-sub'>"
            f"{card.get('subtitle', '')}</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    elif ctype == "description":
        title = card.get("title") or ""

        body = "\n".join(
            str(line) for line in (card.get("text") or [])
        ).strip()

        md = ""

        if title:
            md += f"**{title}**\n\n"

        if body:
            md += body.replace("\n", "  \n")

        with st.container(border=True):
            st.markdown(md)


def render_chips(options: list[str], prefix: str) -> None:
    cols = st.columns(min(len(options), 4))

    for i, opt in enumerate(options[:8]):

        if cols[i % len(cols)].button(opt, key=f"{prefix}-chip-{i}-{opt}"):

            st.session_state.pending = opt


def ask(message: str) -> dict:
    resp = requests.post(
        CHAT_URL,
        json={"message": message, "session_id": st.session_state.sid},
        timeout=60,
    )

    resp.raise_for_status()

    return resp.json()


# ------------------------------------------------------------
# STATE
# ------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "sid" not in st.session_state:
    import uuid

    st.session_state.sid = uuid.uuid4().hex

if "pending" not in st.session_state:
    st.session_state.pending = None


# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
with st.sidebar:

    st.header("🏀 HoopMind")
    st.caption(
        "NBA knowledge assistant — players, teams, "
        "stats, awards, drafts, comparisons."
    )

    st.subheader("Try asking")

    for ex in EXAMPLES:

        if st.button(ex, use_container_width=True):
            st.session_state.pending = ex

    intent_label = None

# ------------------------------------------------------------
# HEADER + HISTORY
# ------------------------------------------------------------
st.title("🏀 HoopMind")
st.caption("Your NBA knowledge assistant")

for m_i, msg in enumerate(st.session_state.messages):

    role = msg["role"]

    with st.chat_message(role):

        if role == "assistant":
            rich = msg.get("rich")
            if rich:
                chips = None
                for row in rich:
                    for card in row:
                        if card["type"] == "chips":
                            chips = [
                                o["text"] for o in card.get("options", [])
                            ]
                        else:
                            render_card(card)

                if chips and msg is st.session_state.messages[-1]:
                    render_chips(chips, f"h{m_i}")
            else:

                st.write(msg.get("text") or "")
        else:

            st.markdown(msg["text"])

# ------------------------------------------------------------
# INPUT (chat box OR clicked chip/example)
# ------------------------------------------------------------
user_input = st.chat_input("Ask about the NBA…")
queued = st.session_state.pending
st.session_state.pending = None
prompt = queued or user_input

if prompt:
    st.session_state.messages.append({"role": "user", "text": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        with st.spinner("Looking it up…"):
            try:
                data = ask(prompt)

            except Exception as exc:

                data = {
                    "rich": None,
                    "text": f"⚠️ Backend unreachable "
                    f"({exc}). Is webhook.py "
                    f"running?",
                }

        rich = data.get("rich")

        text = data.get("text") or ("I could not find that in my NBA dataset.")

        chips = None

        if rich:
            has_non_chip = False
            for row in rich:
                for card in row:
                    if card["type"] == "chips":
                        chips = [o["text"] for o in card.get("options", [])]
                    else:
                        has_non_chip = True
                        render_card(card)
            if not has_non_chip and text:
                st.write(text)
            if chips:
                render_chips(chips, f"n{len(st.session_state.messages)}")

        else:

            st.write(text)

    assistant_entry = {"role": "assistant", "rich": rich, "text": text}

    if not chips:
        # drop chip rows from history (buttons are one-shot)
        if rich:
            cleaned = [
                [c for c in row if c["type"] != "chips"] for row in rich
            ]

            cleaned = [r for r in cleaned if r]

            assistant_entry["rich"] = cleaned or None

            if not assistant_entry["rich"]:
                assistant_entry["text"] = text

    st.session_state.messages.append(assistant_entry)

    if queued:
        st.rerun()
