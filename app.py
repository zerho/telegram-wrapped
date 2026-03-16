import sqlite3
from collections import Counter
import re

import pandas as pd
import plotly.express as px
import streamlit as st

# Italian stopwords
STOPWORDS = {
    "a", "al", "alla", "alle", "agli", "ai", "anche", "ancora", "anzi", "be",
    "beh", "che", "chi", "ci", "cioè", "come", "con", "cosa", "così", "da",
    "dai", "dal", "dalla", "dalle", "degli", "dei", "del", "dell", "della",
    "delle", "dello", "di", "dove", "e", "ed", "eh", "era", "erano", "essere",
    "è", "fa", "fare", "fatto", "fi", "fra", "già", "gli", "ha", "hai", "hanno",
    "ho", "i", "il", "in", "io", "l", "la", "le", "lei", "li", "lo", "lui",
    "ma", "me", "mi", "mia", "mio", "mo", "molto", "nel", "nella", "nelle",
    "no", "noi", "non", "o", "ok", "per", "però", "più", "po", "poi", "pure",
    "quando", "qui", "sa", "se", "sei", "si", "sia", "siamo", "so", "solo",
    "sono", "sta", "stai", "stavo", "su", "sul", "sulla", "sulle", "te", "ti",
    "tra", "tu", "tutti", "tutto", "un", "una", "uno", "vai", "ve", "vi",
    "voi", "https", "http", "www", "com", "it",
}


@st.cache_data
def load_data():
    try:
        con = sqlite3.connect("chat.db")
        df = pd.read_sql("SELECT * FROM messages", con, parse_dates=["timestamp"])
        con.close()
        return df
    except Exception as e:
        st.error(f"Could not load chat.db: {e}\n\nRun `python load_db.py` first.")
        st.stop()


st.set_page_config(page_title="Groupchat Wrapped", layout="wide")
st.title("Groupchat Wrapped")

df = load_data()

# Sidebar filters
st.sidebar.header("Filters")
platforms = st.sidebar.multiselect(
    "Platform", sorted(df["platform"].dropna().unique()), default=list(df["platform"].dropna().unique())
)
convs = st.sidebar.multiselect(
    "Conversation", sorted(df["conversation"].dropna().unique()), default=list(df["conversation"].dropna().unique())
)

filtered = df[df["platform"].isin(platforms) & df["conversation"].isin(convs)]

if filtered.empty:
    st.warning("No messages match the current filters.")
    st.stop()

st.caption(f"{len(filtered):,} messages selected")

# --- Chart 1: Messages per sender ---
counts = filtered["sender"].value_counts().reset_index()
counts.columns = ["sender", "count"]
fig1 = px.bar(
    counts,
    x="count",
    y="sender",
    orientation="h",
    title="Messages per sender",
    labels={"count": "Messages", "sender": ""},
)
fig1.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig1, use_container_width=True)

# --- Chart 2: Messages over time ---
filtered = filtered.copy()
filtered["month"] = filtered["timestamp"].dt.to_period("M").dt.to_timestamp()
over_time = filtered.groupby(["month", "conversation"]).size().reset_index(name="count")
fig2 = px.line(
    over_time,
    x="month",
    y="count",
    color="conversation",
    title="Messages over time (monthly)",
    labels={"month": "Month", "count": "Messages", "conversation": "Chat"},
)
st.plotly_chart(fig2, use_container_width=True)

# --- Chart 3: Activity by hour ---
filtered["hour"] = filtered["timestamp"].dt.hour
by_hour = filtered.groupby("hour").size().reset_index(name="count")
fig3 = px.bar(
    by_hour,
    x="hour",
    y="count",
    title="Activity by hour of day",
    labels={"hour": "Hour (UTC)", "count": "Messages"},
)
fig3.update_xaxes(dtick=1)
st.plotly_chart(fig3, use_container_width=True)

# --- Chart 4: Top words ---
st.subheader("Top words")
col1, col2 = st.columns([1, 3])
with col1:
    top_n = st.slider("Show top N words", 10, 50, 20)
    sender_filter = st.selectbox(
        "Filter by sender", ["All"] + sorted(filtered["sender"].dropna().unique().tolist())
    )

word_source = filtered if sender_filter == "All" else filtered[filtered["sender"] == sender_filter]
all_text = " ".join(word_source["text"].dropna().astype(str).str.lower())
words = re.findall(r"\b[a-záàéèíìóòúùâêîôûäëïöüã]{3,}\b", all_text)
word_counts = Counter(w for w in words if w not in STOPWORDS)
top_words = pd.DataFrame(word_counts.most_common(top_n), columns=["word", "count"])

with col2:
    fig4 = px.bar(
        top_words,
        x="count",
        y="word",
        orientation="h",
        title=f"Top {top_n} words" + (f" — {sender_filter}" if sender_filter != "All" else ""),
        labels={"count": "Occurrences", "word": ""},
    )
    fig4.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig4, use_container_width=True)
