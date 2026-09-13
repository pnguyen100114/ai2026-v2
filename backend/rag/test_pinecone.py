import os
from dotenv import load_dotenv
from pinecone import Pinecone

from embeddings import create_embedding


# ==========================================
# LOAD ENV
# ==========================================

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
PINECONE_NAMESPACE = os.getenv(
    "PINECONE_NAMESPACE",
    "__default__"
)

EMBEDDING_DIMENSION = int(
    os.getenv("EMBEDDING_DIMENSION", "1536")
)


# ==========================================
# CHECK ENV
# ==========================================

if not PINECONE_API_KEY:
    raise ValueError(
        "❌ Chưa có PINECONE_API_KEY"
    )

if not PINECONE_INDEX:
    raise ValueError(
        "❌ Chưa có PINECONE_INDEX"
    )


# ==========================================
# CONNECT PINECONE
# ==========================================

print()
print("==========================================")
print("        TEST PINECONE RAG")
print("==========================================")

print()
print("Index:", PINECONE_INDEX)
print("Namespace:", PINECONE_NAMESPACE)
print("Expected dimension:", EMBEDDING_DIMENSION)


pc = Pinecone(
    api_key=PINECONE_API_KEY
)

index = pc.Index(
    PINECONE_INDEX
)


# ==========================================
# TEST 1: INDEX
# ==========================================

print()
print("------------------------------------------")
print("TEST 1: KẾT NỐI PINECONE")
print("------------------------------------------")

try:

    stats = index.describe_index_stats()

    print("✓ Kết nối Pinecone thành công")

except Exception as error:

    print("❌ Không kết nối được Pinecone")
    print(error)
    exit()


# ==========================================
# TEST 2: VECTOR COUNT
# ==========================================

print()
print("------------------------------------------")
print("TEST 2: KIỂM TRA SỐ VECTOR")
print("------------------------------------------")

try:

    namespace_stats = stats.get(
        "namespaces",
        {}
    )

    if PINECONE_NAMESPACE in namespace_stats:

        vector_count = namespace_stats[
            PINECONE_NAMESPACE
        ].get(
            "vector_count",
            0
        )

    else:

        vector_count = 0

    print(
        "Vector trong namespace:",
        vector_count
    )

    if vector_count > 0:

        print(
            "✓ Đã có dữ liệu trong Pinecone"
        )

    else:

        print(
            "❌ Namespace hiện chưa có vector"
        )

except Exception as error:

    print(
        "❌ Không kiểm tra được vector count"
    )

    print(error)


# ==========================================
# TEST 3: INDEX STATS
# ==========================================

print()
print("------------------------------------------")
print("TEST 3: INDEX STATS")
print("------------------------------------------")

try:

    print(
        stats
    )

except Exception as error:

    print(error)


# ==========================================
# TEST 4: QUERY SGK
# ==========================================

print()
print("------------------------------------------")
print("TEST 4: QUERY DỮ LIỆU SGK")
print("------------------------------------------")

query_text = "Hãy giải thích kiến thức trong bài học này."

print()
print("Query:")
print(query_text)

try:

    print()
    print(
        "Gemini đang tạo embedding query..."
    )

    query_vector = create_embedding(
        query_text
    )

    if len(query_vector) != EMBEDDING_DIMENSION:

        print(
            "❌ Sai embedding dimension"
        )

        print(
            "Actual:",
            len(query_vector)
        )

        print(
            "Expected:",
            EMBEDDING_DIMENSION
        )

        exit()

    print(
        "✓ Query embedding OK"
    )

    # Query Pinecone

    result = index.query(

        vector=query_vector,

        top_k=5,

        include_metadata=True,

        namespace=PINECONE_NAMESPACE

    )

    matches = result.get(
        "matches",
        []
    )

    print()
    print(
        "Số kết quả:",
        len(matches)
    )

    if len(matches) == 0:

        print(
            "❌ Pinecone không trả về dữ liệu"
        )

    else:

        print()
        print(
            "✓ QUERY THÀNH CÔNG"
        )

        print()

        for i, match in enumerate(
            matches,
            start=1
        ):

            metadata = match.get(
                "metadata",
                {}
            )

            print(
                "================================"
            )

            print(
                f"Kết quả #{i}"
            )

            print(
                "ID:",
                match.get("id")
            )

            print(
                "Score:",
                match.get("score")
            )

            print(
                "Subject:",
                metadata.get(
                    "subject"
                )
            )

            print(
                "Grade:",
                metadata.get(
                    "grade"
                )
            )

            print(
                "Volume:",
                metadata.get(
                    "volume"
                )
            )

            print(
                "Chapter:",
                metadata.get(
                    "chapter"
                )
            )

            print(
                "Lesson:",
                metadata.get(
                    "lesson"
                )
            )

            print(
                "Page:",
                metadata.get(
                    "page"
                )
            )

            print(
                "Source:",
                metadata.get(
                    "source"
                )
            )

            text = metadata.get(
                "text",
                ""
            )

            print()
            print(
                "Nội dung:"
            )

            print(
                text[:500]
            )


except Exception as error:

    print()
    print(
        "❌ QUERY THẤT BẠI"
    )

    print(error)


# ==========================================
# FINISH
# ==========================================

print()
print("==========================================")
print("              KẾT THÚC TEST")
print("==========================================")