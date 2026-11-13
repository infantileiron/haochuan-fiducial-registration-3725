import json, sqlite3, threading
from contextlib import contextmanager
from dataclasses import asdict
from fastapi import HTTPException
from src.config.settings import DATABASE_URL
TABLES = ("datasets", "frames", "studies", "runs", "reviews", "reports", "users", "audit")
_LOCK = threading.RLock()
def connect():
    if DATABASE_URL.startswith("sqlite:///"):
        conn = sqlite3.connect(DATABASE_URL.removeprefix("sqlite:///"), timeout=30)
        return conn, "?"
    import psycopg
    return psycopg.connect(DATABASE_URL), "%s"
def init_db():
    conn,_ = connect()
    try:
        if not DATABASE_URL.startswith("sqlite:///"):
            conn.execute("SELECT pg_advisory_xact_lock(2405)")
        for table in TABLES:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        conn.commit()
    finally: conn.close()
@contextmanager
def transaction():
    """串行化审批/撤销/报告生成等复合写操作。

    进程内用 RLock 互斥；数据库事务保证多条 payload 读写的原子性，
    SQLite 依赖写锁、PostgreSQL 依赖行锁与事务隔离。
    """
    conn,q = connect()
    with _LOCK:
        if DATABASE_URL.startswith("sqlite:///"):
            conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn,q
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
def all_rows(table):
    assert table in TABLES
    conn,_ = connect()
    try: return [json.loads(row[0]) for row in conn.execute(f"SELECT payload FROM {table} ORDER BY id").fetchall()]
    finally: conn.close()
def get(table, id):
    assert table in TABLES
    conn,q = connect()
    try:
        row = conn.execute(f"SELECT payload FROM {table} WHERE id={q}", (id,)).fetchone()
        if row is None: raise HTTPException(404, "记录不存在")
        return json.loads(row[0])
    finally: conn.close()
def tx_get(conn,q,table,id):
    assert table in TABLES
    row = conn.execute(f"SELECT payload FROM {table} WHERE id={q}", (id,)).fetchone()
    if row is None: raise HTTPException(404, "记录不存在")
    return json.loads(row[0])
def tx_all_rows(conn,q,table):
    assert table in TABLES
    return [json.loads(row[0]) for row in conn.execute(f"SELECT payload FROM {table} ORDER BY id").fetchall()]
def tx_put(conn,q,table,item,insert_only=False):
    assert table in TABLES
    if not isinstance(item, dict): item = asdict(item)
    clause = "DO NOTHING" if insert_only else "DO UPDATE SET payload=excluded.payload"
    conn.execute(f"INSERT INTO {table} (id,payload) VALUES ({q},{q}) ON CONFLICT(id) {clause}", (item["id"], json.dumps(item, ensure_ascii=False, allow_nan=False)))
    return item
def put(table, item, insert_only=False):
    assert table in TABLES
    if not isinstance(item, dict): item = asdict(item)
    conn,q = connect()
    try:
        with _LOCK:
            tx_put(conn,q,table,item,insert_only)
            conn.commit()
        return item
    except Exception:
        conn.rollback()
        raise
    finally: conn.close()
