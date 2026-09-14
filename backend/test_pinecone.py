import os
import sys
import types

# Windows: pinecone imports readline, which is not available there
sys.modules.setdefault("readline", types.ModuleType("readline"))

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX", "ai-tutor-sgk")
NAMESPACE = os.getenv("PINECONE_NAMESPACE", "")

if not API_KEY:
    sys.exit("Thiếu PINECONE_API_KEY trong backend/.env")

try:
    pc = Pinecone(api_key=API_KEY)
    index = pc.Index(INDEX_NAME)

    # 1. Kiểm tra trạng thái index
    stats = index.describe_index_stats()
    dim = stats.get("dimension")
    namespaces = stats.get("namespaces", {})

    print(f" Kết nối Index thành công! (Dimension: {dim})")
    print(f" Danh sách namespace hiện có: {list(namespaces.keys())}")

    # 2. Truy vấn thử một vector giả
    target_ns = NAMESPACE if NAMESPACE in namespaces else ("" if "" in namespaces else None)

    if target_ns is not None:
        res = index.query(
            vector=[0.0] * dim,
            top_k=2,
            namespace=target_ns,
            include_metadata=True
        )
        print(f" Truy vấn namespace '{target_ns}' thành công! Tìm thấy {len(res['matches'])} kết quả.")
    else:
        print(f" Không tìm thấy dữ liệu trong namespace '{NAMESPACE}'.")

except Exception as e:
    print(f" Thất bại: {e}")
