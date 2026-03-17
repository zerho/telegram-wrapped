"""
Sentiment analysis for chat messages using MilaNLProc/feel-it-italian-sentiment.
Runs once offline and populates the `sentiment` table in chat.db.

Usage:
    python src/analyze_sentiment.py

Estimated runtime: ~25-40 min on Apple Silicon MPS, ~90-120 min on CPU.
"""
import re
import sqlite3

import pandas as pd
import torch
from transformers import PreTrainedTokenizerFast, pipeline

DB = "chat.db"
MODEL = "MilaNLProc/feel-it-italian-sentiment"
BATCH_SIZE = 64
MAX_LEN = 128
WA_REPLY_WINDOW_SECS = 180  # 3-minute proximity window for WA reply inference


def init_schema(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS sentiment (
            platform      TEXT NOT NULL,
            conversation  TEXT NOT NULL,
            msg_id        REAL NOT NULL,
            sender        TEXT,
            label         TEXT,
            score         REAL,
            reply_target  TEXT,
            reply_source  TEXT,
            PRIMARY KEY (platform, conversation, msg_id)
        )
    """)
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_sentiment_platform_conv "
        "ON sentiment(platform, conversation)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_sentiment_reply_target "
        "ON sentiment(reply_target)"
    )
    con.commit()


def load_pending(con):
    """Return messages that have not yet been scored (idempotent)."""
    return pd.read_sql(
        """
        SELECT m.rowid AS msg_id,
               m.platform,
               m.conversation,
               m.sender,
               m.text,
               m.timestamp,
               m.id        AS tg_id,
               m.reply_to_id
        FROM   messages m
        LEFT JOIN sentiment s
               ON  s.platform     = m.platform
               AND s.conversation = m.conversation
               AND s.msg_id       = m.rowid
        WHERE  s.msg_id IS NULL
        """,
        con,
    )


def is_scorable(text):
    if not isinstance(text, str) or len(text) < 5:
        return False
    return bool(re.search(r"[a-zA-ZÀ-ÿ]", text))


def resolve_tg_reply_targets(df, con):
    """Map reply_to_id → sender for Telegram explicit replies."""
    tg_replies = df[
        (df["platform"] == "telegram")
        & df["reply_to_id"].notna()
        & (df["reply_to_id"].astype(str).str.strip() != "")
    ]
    if tg_replies.empty:
        return {}

    raw_ids = tg_replies["reply_to_id"].dropna().unique().tolist()
    float_ids = []
    for x in raw_ids:
        try:
            float_ids.append(float(x))
        except (ValueError, TypeError):
            pass
    if not float_ids:
        return {}

    targets = {}
    chunk_size = 500
    for i in range(0, len(float_ids), chunk_size):
        chunk = float_ids[i : i + chunk_size]
        placeholders = ",".join("?" * len(chunk))
        rows = con.execute(
            f"""
            SELECT CAST(id AS REAL) AS id_real, sender
            FROM   messages
            WHERE  CAST(id AS REAL) IN ({placeholders})
            """,
            chunk,
        ).fetchall()
        for id_real, sender in rows:
            targets[id_real] = sender

    return targets


def infer_wa_reply_targets(df_conv):
    """
    For each WA message, scan back ≤3 minutes for the most recent message
    from a *different* sender.  Returns {msg_id: sender | None}.
    """
    df_conv = df_conv.copy().sort_values("timestamp").reset_index(drop=True)
    df_conv["ts"] = pd.to_datetime(df_conv["timestamp"], utc=True, errors="coerce")

    reply_targets = {}
    for i, row in df_conv.iterrows():
        t = row["ts"]
        if pd.isna(t):
            reply_targets[row["msg_id"]] = None
            continue
        window_start = t - pd.Timedelta(seconds=WA_REPLY_WINDOW_SECS)
        candidates = df_conv[
            (df_conv.index < i)
            & (df_conv["ts"] >= window_start)
            & (df_conv["sender"] != row["sender"])
        ]
        reply_targets[row["msg_id"]] = (
            candidates.iloc[-1]["sender"] if not candidates.empty else None
        )

    return reply_targets


def main():
    if torch.backends.mps.is_available():
        device_str = "mps"
    elif torch.cuda.is_available():
        device_str = "cuda"
    else:
        device_str = "cpu"
    print(f"Using device: {device_str}")

    con = sqlite3.connect(DB)
    init_schema(con)

    pending = load_pending(con)
    if pending.empty:
        print("No pending messages to score — all messages already in sentiment table.")
        con.close()
        return

    mask = pending["text"].apply(is_scorable)
    scorable = pending[mask].copy()
    skipped = len(pending) - len(scorable)
    print(
        f"Messages to score: {len(scorable):,}  (skipped {skipped:,} non-text / too-short)"
    )

    print(f"Loading model {MODEL} …")
    # PreTrainedTokenizerFast loads from tokenizer.json (Rust tokenizers lib),
    # bypassing the buggy CamemBERT Python __init__ (sentencepiece 3-tuple issue)
    tokenizer = PreTrainedTokenizerFast.from_pretrained(MODEL)
    classifier = pipeline(
        "text-classification",
        model=MODEL,
        tokenizer=tokenizer,
        device=device_str,
        truncation=True,
        max_length=MAX_LEN,
    )

    texts = scorable["text"].tolist()
    results = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        preds = classifier(batch, truncation=True, max_length=MAX_LEN)
        results.extend(preds)
        done = i + len(batch)
        if done % (BATCH_SIZE * 10) == 0 or done == len(texts):
            print(f"  {done:,}/{len(texts):,} scored …")

    scorable = scorable.copy()
    scorable["label"] = [r["label"].lower() for r in results]
    scorable["score"] = [float(r["score"]) for r in results]

    # --- Telegram explicit replies ---
    tg_targets = resolve_tg_reply_targets(scorable, con)

    def tg_reply_target(row):
        rid = row.get("reply_to_id")
        if pd.isna(rid) or str(rid).strip() == "":
            return None
        try:
            return tg_targets.get(float(rid))
        except (ValueError, TypeError):
            return None

    # --- WhatsApp proximity replies ---
    wa_reply_map = {}
    wa_df = scorable[scorable["platform"] != "telegram"]
    for _conv, grp in wa_df.groupby("conversation"):
        wa_reply_map.update(infer_wa_reply_targets(grp))

    def reply_info(row):
        if row["platform"] == "telegram":
            target = tg_reply_target(row)
            source = "explicit" if target is not None else None
        else:
            target = wa_reply_map.get(row["msg_id"])
            source = "inferred" if target is not None else None
        return pd.Series({"reply_target": target, "reply_source": source})

    scorable[["reply_target", "reply_source"]] = scorable.apply(reply_info, axis=1)

    rows = scorable[
        ["platform", "conversation", "msg_id", "sender",
         "label", "score", "reply_target", "reply_source"]
    ].values.tolist()

    con.executemany(
        """
        INSERT OR REPLACE INTO sentiment
            (platform, conversation, msg_id, sender, label, score, reply_target, reply_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    con.commit()
    con.close()
    print(f"Done! Inserted {len(rows):,} sentiment rows into {DB}.")


if __name__ == "__main__":
    main()
