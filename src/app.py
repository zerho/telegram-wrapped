import sqlite3
from collections import Counter
import re

import numpy as np
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
    "voi", "https", "http", "www", "com", "it", "sto", "due", "fai", "vuoi"
}

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@st.cache_data
def load_sentiment():
    try:
        con = sqlite3.connect("chat.db")
        # Check table exists before querying
        exists = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sentiment'"
        ).fetchone()
        if not exists:
            con.close()
            return None
        df = pd.read_sql("SELECT * FROM sentiment", con)
        con.close()
        return df
    except Exception:
        return None


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

filtered = df[df["platform"].isin(platforms) & df["conversation"].isin(convs)].copy()

if filtered.empty:
    st.warning("No messages match the current filters.")
    st.stop()

# --- Summary stats ---
participants = sorted(filtered["sender"].dropna().unique().tolist())
first_msg = filtered.loc[filtered["timestamp"].idxmin()]
last_msg = filtered.loc[filtered["timestamp"].idxmax()]

col_a, col_b, col_c = st.columns(3)
col_a.metric("First message", first_msg["timestamp"].strftime("%Y-%m-%d"), first_msg["sender"])
col_b.metric("Last message", last_msg["timestamp"].strftime("%Y-%m-%d"), last_msg["sender"])
col_c.metric("Participants", len(participants))
st.caption("**Participants:** " + ", ".join(participants))
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

# --- Chart 2: Messages per month ---
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

# --- Chart 3: Messages per weekday ---
filtered["weekday"] = filtered["timestamp"].dt.day_name()
by_weekday = filtered.groupby("weekday").size().reindex(WEEKDAY_ORDER).reset_index(name="count")
fig3 = px.bar(
    by_weekday,
    x="weekday",
    y="count",
    title="Messages by day of week",
    labels={"weekday": "", "count": "Messages"},
)
st.plotly_chart(fig3, use_container_width=True)

# --- Chart 4: Activity by hour (stacked by sender) ---
filtered["hour"] = filtered["timestamp"].dt.hour
by_hour_sender = filtered.groupby(["hour", "sender"]).size().reset_index(name="count")
fig4 = px.bar(
    by_hour_sender,
    x="hour",
    y="count",
    color="sender",
    title="Activity by hour of day",
    labels={"hour": "Hour (UTC)", "count": "Messages", "sender": "Sender"},
    barmode="stack",
)
fig4.update_xaxes(dtick=1)
st.plotly_chart(fig4, use_container_width=True)

# --- Chart 5: Top words ---
st.subheader("Top words")
col1, col2 = st.columns([1, 3])
with col1:
    top_n = st.slider("Show top N words", 10, 50, 20)
    sender_filter = st.selectbox(
        "Filter by sender", ["All"] + sorted(filtered["sender"].dropna().unique().tolist())
    )

word_source = filtered if sender_filter == "All" else filtered[filtered["sender"] == sender_filter]
all_text = " ".join(word_source["text"].dropna().astype(str).str.lower())
words = re.findall(r"\b[a-záàéèíìóòúùâêîôûäëïöüã]{4,}\b", all_text)
word_counts = Counter(w for w in words if w not in STOPWORDS)
top_words = pd.DataFrame(word_counts.most_common(top_n), columns=["word", "count"])

with col2:
    fig5 = px.bar(
        top_words,
        x="count",
        y="word",
        orientation="h",
        title=f"Top {top_n} words" + (f" — {sender_filter}" if sender_filter != "All" else ""),
        labels={"count": "Occurrences", "word": ""},
    )
    fig5.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig5, use_container_width=True)

# --- Fun facts per person ---
st.subheader("Fun facts per person")

def person_stats(grp):
    texts = grp["text"].dropna().astype(str).str.strip()
    texts = texts[texts != ""]
    all_words = " ".join(texts.str.lower()).split()
    char_lengths = texts.str.len()
    return pd.Series({
        "messages": len(grp),
        "total_words": len(all_words),
        "avg_msg_length": round(char_lengths.mean(), 1) if not char_lengths.empty else 0.0,
        "unique_words": len(set(all_words)),
        "longest_msg_chars": int(char_lengths.max()) if not char_lengths.empty else 0,
    })

stats = filtered.groupby("sender").apply(person_stats).reset_index()
stats.columns = ["Sender", "Messages", "Total words", "Avg msg length", "Unique words", "Longest msg (chars)"]
st.dataframe(stats.set_index("Sender"), use_container_width=True)

# --- Sentiment Analysis ---
st.subheader("Sentiment Analysis")

sdf = load_sentiment()

if sdf is None:
    st.info("Run `python src/analyze_sentiment.py` to generate sentiment data.")
else:
    # Apply the same sidebar filters to sentiment data
    sdf = sdf[sdf["platform"].isin(platforms) & sdf["conversation"].isin(convs)].copy()

    if sdf.empty:
        st.info("No sentiment data for the current filters.")
    else:
        # Signed score: +score if positive, -score if negative
        sdf["signed_score"] = sdf.apply(
            lambda r: r["score"] if r["label"] == "positive" else -r["score"], axis=1
        )

        # --- Chart A: Per-sender positivity index ---
        positivity = (
            sdf.groupby("sender")["signed_score"]
            .mean()
            .reset_index(name="positivity_index")
            .sort_values("positivity_index")
        )
        positivity["color"] = positivity["positivity_index"].apply(
            lambda x: "positive" if x >= 0 else "negative"
        )
        fig_a = px.bar(
            positivity,
            x="positivity_index",
            y="sender",
            orientation="h",
            color="color",
            color_discrete_map={"positive": "#2ecc71", "negative": "#e74c3c"},
            title="Chart A — Per-sender positivity index (mean signed sentiment score)",
            labels={"positivity_index": "Mean signed score (−1 to +1)", "sender": ""},
        )
        fig_a.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
        st.plotly_chart(fig_a, use_container_width=True)
        st.caption("WhatsApp messages are included here. Negative = tends negative, Positive = tends positive.")

        # Controls for heatmaps B and C
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            min_replies = st.slider("Minimum reply count to show (Charts B & C)", 1, 20, 3)
            include_inferred = st.checkbox(
                "Include WhatsApp inferred replies in Charts B & C", value=False
            )

        # Filter to reply rows
        reply_df = sdf[sdf["reply_target"].notna()].copy()
        if not include_inferred:
            reply_df = reply_df[reply_df["reply_source"] != "inferred"]

        if reply_df.empty:
            st.info("No reply data available for Charts B & C with current settings.")
        else:
            # Compute reply count matrix (for masking low-count cells)
            count_matrix = (
                reply_df.groupby(["sender", "reply_target"])
                .size()
                .reset_index(name="count")
            )
            count_pivot = count_matrix.pivot(
                index="sender", columns="reply_target", values="count"
            ).fillna(0)

            # Mask cells below minimum
            mask = count_pivot >= min_replies

            # Sentiment heatmap
            sent_matrix = (
                reply_df.groupby(["sender", "reply_target"])["signed_score"]
                .mean()
                .reset_index(name="mean_score")
            )
            sent_pivot = sent_matrix.pivot(
                index="sender", columns="reply_target", values="mean_score"
            )

            # Apply mask: NaN out low-count cells in both pivots
            all_senders = sorted(
                set(sent_pivot.index.tolist()) | set(count_pivot.index.tolist())
            )
            all_targets = sorted(
                set(sent_pivot.columns.tolist()) | set(count_pivot.columns.tolist())
            )
            sent_pivot = sent_pivot.reindex(index=all_senders, columns=all_targets)
            count_pivot = count_pivot.reindex(index=all_senders, columns=all_targets).fillna(0)
            mask = count_pivot >= min_replies
            sent_pivot_masked = sent_pivot.where(mask)

            # --- Chart B: Directional reply sentiment heatmap ---
            fig_b = px.imshow(
                sent_pivot_masked,
                color_continuous_scale="RdYlGn",
                color_continuous_midpoint=0,
                title="Chart B — Reply sentiment heatmap (row = replier, col = replied-to)",
                labels={"color": "Mean signed score"},
                aspect="auto",
            )
            fig_b.update_xaxes(title="Replied-to person")
            fig_b.update_yaxes(title="Replier")
            st.plotly_chart(fig_b, use_container_width=True)
            st.caption(
                "Red cell = replier tends to reply negatively to that person. "
                "Cells with fewer than the minimum reply count are hidden."
            )

            # --- Chart C: Reply volume heatmap ---
            count_pivot_masked = count_pivot.where(mask).replace(0, np.nan)
            fig_c = px.imshow(
                count_pivot_masked,
                color_continuous_scale="Blues",
                title="Chart C — Reply volume heatmap (contextualises Chart B)",
                labels={"color": "Reply count"},
                aspect="auto",
            )
            fig_c.update_xaxes(title="Replied-to person")
            fig_c.update_yaxes(title="Replier")
            st.plotly_chart(fig_c, use_container_width=True)
            st.caption(
                "Low-count cells in Chart B may be noise. "
                + ("WhatsApp inferred replies included." if include_inferred
                   else "WhatsApp inferred replies excluded (toggle above to include).")
            )
