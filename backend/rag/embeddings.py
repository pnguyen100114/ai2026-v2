import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ==========================================
# LOAD ENV
# ==========================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "gemini-embedding-001"
)

EMBEDDING_DIMENSION = int(
    os.getenv(
        "EMBEDDING_DIMENSION",
        "1536"
    )
)


# ==========================================
# CHECK API KEY
# ==========================================

if not GEMINI_API_KEY:
    raise ValueError(
        "Chưa có GEMINI_API_KEY trong .env"
    )


# ==========================================
# GEMINI CLIENT
# ==========================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ==========================================
# CREATE ONE EMBEDDING
# ==========================================

def create_embedding(text):

    if not text or not text.strip():
        return []

    while True:

        try:

            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=EMBEDDING_DIMENSION
                )
            )

            return result.embeddings[0].values

        except Exception as error:

            error_text = str(error)

            if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:

                print()
                print("⚠ Gemini đang giới hạn request.")
                print("→ Chờ 10 giây rồi thử lại...")

                time.sleep(10)

            else:

                raise error


# ==========================================
# CREATE MANY EMBEDDINGS
# ==========================================

def create_embeddings(texts):

    if not texts:
        return []

    all_embeddings = []

    # Không gửi quá nhiều request liên tục
    for i, text in enumerate(texts):

        print(
            f"  Embedding {i + 1}/{len(texts)}"
        )

        embedding = create_embedding(
            text
        )

        all_embeddings.append(
            embedding
        )

        # Nghỉ giữa các request
        if i < len(texts) - 1:

            time.sleep(1)

    return all_embeddings