import sqlite3

# 查向量库：看 chunk 是否带时间戳
def check_vector_store():
    conn = sqlite3.connect("data/vector_store.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 先看看有哪些 video_id
    cur.execute("SELECT DISTINCT video_id FROM video_chunk_vectors LIMIT 10")
    videos = cur.fetchall()
    print("=== 向量库中的视频 ===")
    for v in videos:
        print(f"  video_id: {v['video_id']}")

    # 查某个视频（改成你实际测试的 BV 号）
    video_id = "BV11K411d7V8_p1"  # ← 改成你的实际 video_id
    cur.execute("""
                SELECT chunk_id, start_time, end_time, substr(content,1,40) as preview
                FROM video_chunk_vectors
                WHERE video_id = ?
                LIMIT 5
                """, (video_id,))

    print(f"\n=== video_id={video_id} 的 chunks ===")
    rows = cur.fetchall()
    if not rows:
        print("  没有数据！")
    for r in rows:
        print(f"  chunk_id={r['chunk_id']}, start={r['start_time']}, end={r['end_time']}")
        print(f"    内容: {r['preview']}...")

    conn.close()

# 查视频库：看原始 segments 是否带时间戳
def check_video_store():
    conn = sqlite3.connect("data/video_store.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    video_id = "BV1xx_p1"  # ← 改成你的实际 video_id
    cur.execute("""
                SELECT segment_index, start_time, end_time, substr(content,1,40) as preview
                FROM transcript_segments
                WHERE video_id = ?
                LIMIT 5
                """, (video_id,))

    print(f"\n=== video_store 的 segments (video_id={video_id}) ===")
    for r in cur.fetchall():
        print(f"  idx={r['segment_index']}, start={r['start_time']}, end={r['end_time']}")
        print(f"    内容: {r['preview']}...")

    conn.close()

if __name__ == "__main__":
    check_vector_store()
    check_video_store()