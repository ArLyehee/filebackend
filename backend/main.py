from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote
import zipfile
import io
import os

# ============================================
# FastAPI 초기화
# ============================================
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ============================================
# DB 연결
# ============================================
DB_USER = "admin"
DB_PASS = "1234"
DB_HOST = "localhost"
DB_PORT = "1521"
DB_SERVICE = "xe"

DATABASE_URL = f"oracle+cx_oracle://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/?service_name={DB_SERVICE}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)



# ============================================
# 카테고리 조회
# ============================================
@app.get("/api/categories")
def get_categories():
    session = SessionLocal()
    try:
        query = text("""
            SELECT DISTINCT CATEGORY AS category
            FROM FILES
            WHERE CATEGORY IS NOT NULL
            ORDER BY CATEGORY
        """)
        categories = [row["category"] for row in session.execute(query).mappings().all()]
        return {"categories": categories}
    finally:
        session.close()

# ============================================
# 카테고리별 파일 조회
# ============================================
@app.get("/api/files/category/{category}")
def list_files_by_category(category: str):
    session = SessionLocal()
    try:
        query = text("""
            SELECT FILE_NAME AS file_name, FILE_PATH AS file_path
            FROM FILES
            WHERE CATEGORY = :category
              AND HIDE = 0
        """)
        results = session.execute(query, {"category": category}).mappings().all()
        if not results:
            raise HTTPException(status_code=404, detail="해당 카테고리에 파일이 없습니다.")

        files = [
            {
                "file_name": row["file_name"],
                "file_path": row["file_path"]
            }
            for row in results
        ]
        return {"files": files, "count": len(files)}
    finally:
        session.close()

# ============================================
# 카테고리별 파일 전체 조회
# ============================================

@app.get("/api/files")
def get_files_by_category():
    """
    DB에서 카테고리별 파일 목록 전체를 가져와서 JSON으로 반환
    구조: {"카테고리1": [{"file_name": "...", "file_path": "..."}, ...], ...}
    """
    session = SessionLocal()
    try:
        query = text("""
            SELECT FILE_NAME AS file_name, FILE_PATH AS file_path, CATEGORY AS category
            FROM FILES
            WHERE CATEGORY IS NOT NULL AND HIDE = 0
        """)
        results = session.execute(query).mappings().all()

        files_by_category = {}
        for row in results:
            cat = row["category"]
            if cat not in files_by_category:
                files_by_category[cat] = []
            files_by_category[cat].append({
                "file_name": row["file_name"],
                "file_path": row["file_path"]
            })
        return files_by_category
    finally:
        session.close()
# ============================================
# 카테고리별 ZIP 다운로드
# ============================================
@app.get("/api/download/category/{category}")
def download_category_zip(category: str):
    session = SessionLocal()
    try:
        query = text("""
            SELECT FILE_NAME AS file_name, FILE_PATH AS file_path
            FROM FILES
            WHERE CATEGORY = :category
              AND HIDE = 0
        """)
        results = session.execute(query, {"category": category}).mappings().all()
        if not results:
            raise HTTPException(status_code=404, detail="해당 카테고리에 파일이 없습니다.")

        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for row in results:
                file_path = row["file_path"]
                if os.path.exists(file_path):
                    zf.write(file_path, arcname=row["file_name"])
                else:
                    print(f"[경고] 파일 없음: {file_path}")

        mem_zip.seek(0)
        filename_encoded = quote(f"{category}.zip")
        return StreamingResponse(
            mem_zip,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"}
        )
    finally:
        session.close()

# ============================================
# 전체 파일 ZIP 다운로드
# ============================================
@app.get("/api/download/all")
def download_all_files_by_category():
    session = SessionLocal()
    try:
        # HIDE=0인 파일 조회
        files = session.execute(text("""
            SELECT FILE_NAME AS file_name, FILE_PATH AS file_path,
                   CATEGORY AS category
            FROM FILES
            WHERE HIDE = 0
        """)).mappings().all()

        if not files:
            raise HTTPException(status_code=404, detail="다운로드할 파일이 없습니다.")

        mem_zip = io.BytesIO()
        added_files = 0
        with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for row in files:
                file_path = row["file_path"]
                category = row["category"] or "기타"
                if file_path and os.path.exists(file_path):
                    # 카테고리별 폴더 구조로 ZIP에 추가
                    arcname = f"{category}/{row['file_name']}"
                    zf.write(file_path, arcname=arcname)
                    added_files += 1
                else:
                    print(f"[경고] 파일 없음: {file_path}")

        if added_files == 0:
            raise HTTPException(status_code=404, detail="다운로드할 실제 파일이 없습니다.")

        mem_zip.seek(0)
        return StreamingResponse(
            mem_zip,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=all_documents_by_category.zip"}
        )
    finally:
        session.close()


# ============================================
# 카테고리별 파일 미리보기
# ============================================
@app.get("/api/files/preview")
def get_files_preview(limit: int = Query(5, ge=1)):
    """
    카테고리별 최대 limit개 파일 + 총 개수 반환
    """
    session = SessionLocal()
    try:
        # 전체 파일 조회
        query = text("""
            SELECT FILE_NAME AS file_name, FILE_PATH AS file_path, CATEGORY AS category
            FROM FILES
            WHERE CATEGORY IS NOT NULL AND HIDE = 0
            ORDER BY CATEGORY, FILE_NAME
        """)
        results = session.execute(query).mappings().all()

        files_by_category = {}
        counts = {}

        for row in results:
            cat = row["category"]
            if cat not in files_by_category:
                files_by_category[cat] = []
                counts[cat] = 0
            counts[cat] += 1
            if len(files_by_category[cat]) < limit:
                files_by_category[cat].append({
                    "file_name": row["file_name"],
                    "file_path": row["file_path"]
                })

        # 구조: { "법률안": { "files": [...], "total_count": 7 }, ... }
        result = {cat: {"files": files_by_category[cat], "total_count": counts[cat]} for cat in files_by_category}
        return result
    finally:
        session.close()
