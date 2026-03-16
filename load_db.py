import sqlite3
import pandas as pd
from glob import glob

DB = "chat.db"
WA_FMT = "%d/%m/%y, %H:%M:%S"
TG_FMT = "%d.%m.%Y %H:%M:%S UTC%z"


def load_csv(path, fmt):
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format=fmt, errors="coerce", utc=True)
    return df


dfs = []
for f in glob("formatted/wa/*.csv"):
    dfs.append(load_csv(f, WA_FMT))
for f in glob("formatted/tg/*.csv"):
    dfs.append(load_csv(f, TG_FMT))

if not dfs:
    print("No CSV files found in formatted/wa/ or formatted/tg/")
    print("Run the converters first: node tg_convert.js <folder> / node wa_convert.js <file>")
    exit(1)

df = pd.concat(dfs, ignore_index=True)

con = sqlite3.connect(DB)
df.to_sql("messages", con, if_exists="replace", index=False)
con.close()
print(f"Loaded {len(df)} messages into {DB}")
