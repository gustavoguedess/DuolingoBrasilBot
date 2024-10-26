import pandas as pd

df = pd.read_csv('src/words/english.csv', header=None, names=['word'], sep=';')
df = df.dropna()
df = df[~df.word.str.contains('[^\w]')] # remove non-word characters
df = df[~df.word.str.contains('[0-9]')] # remove words with numbers
unique_words = df.word.unique()
print(len(unique_words))

from txtai import Embeddings

embeddings = Embeddings(
    content=True,
    similarity={
        "path": "sentence-transformers/all-MiniLM-L6-v2",
    }
)
embeddings.index(unique_words)

import os
os.makedirs("src/embeddings/english", exist_ok=True)

# save
embeddings.save("src/embeddings/english")
