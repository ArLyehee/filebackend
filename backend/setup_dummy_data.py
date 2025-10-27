import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ========================
# 1. 테스트 파일 생성
# ========================
os.makedirs("C:/TestFiles", exist_ok=True)

# 카테고리별 샘플 파일 (파일명, 내용)
sample_files = [
    # 법률안
    ("법률안_001.pdf", "법률안 테스트 내용 1"),
    ("법률안_002.pdf", "법률안 테스트 내용 2"),
    ("법률안_003.pdf", "법률안 테스트 내용 3"),
    ("법률안_004.pdf", "법률안 테스트 내용 4"),
    ("법률안_005.pdf", "법률안 테스트 내용 5"),

    # 입법
    ("입법_001.docx", "입법 테스트 내용 1"),
    ("입법_002.docx", "입법 테스트 내용 2"),
    ("입법_003.docx", "입법 테스트 내용 3"),
    ("입법_004.docx", "입법 테스트 내용 4"),
    ("입법_005.docx", "입법 테스트 내용 5"),

    # 보고서
    ("보고서_001.pdf", "보고서 테스트 내용 1"),
    ("보고서_002.pdf", "보고서 테스트 내용 2"),
    ("보고서_003.pdf", "보고서 테스트 내용 3"),
    ("보고서_004.pdf", "보고서 테스트 내용 4"),
    ("보고서_005.pdf", "보고서 테스트 내용 5"),
    ("보고서_006.pdf", "보고서 테스트 내용 2"),
    ("보고서_007.pdf", "보고서 테스트 내용 2"),

    # 회의록
    ("회의록_001.txt", "회의록 테스트 내용 1"),
    ("회의록_002.txt", "회의록 테스트 내용 2"),
    ("회의록_003.txt", "회의록 테스트 내용 3"),
    ("회의록_004.txt", "회의록 테스트 내용 4"),
    ("회의록_005.txt", "회의록 테스트 내용 5"),

    # 기타
    ("공지사항_001.txt", "공지사항 테스트 내용 1"),
    ("공지사항_002.txt", "공지사항 테스트 내용 2"),
]

# 파일 생성
for fname, content in sample_files:
    with open(f"C:/TestFiles/{fname}", "w", encoding="utf-8") as f:
        f.write(content)

# ========================
# 2. JSON 더미 생성
# ========================
dummy_json = [
    {
        "name": fname,
        "type": fname.split('.')[-1],
        "path": f"C:/TestFiles/{fname}",
        "category": (
            "법률안" if "법률안" in fname else
            "입법" if "입법" in fname else
            "보고서" if "보고서" in fname else
            "회의록" if "회의록" in fname else
            "기타"
        )
    }
    for fname, _ in sample_files
]

# JSON 파일 저장
with open("dummy_files.json", "w", encoding="utf-8") as f:
    json.dump(dummy_json, f, ensure_ascii=False, indent=4)

# ========================
# 3. Oracle DB 연결
# ========================
DB_USER = "admin"
DB_PASS = "1234"
DB_HOST = "localhost"
DB_PORT = "1521"
DB_SERVICE = "xe"

DATABASE_URL = f"oracle+cx_oracle://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/?service_name={DB_SERVICE}"
engine = create_engine(
    DATABASE_URL,
    connect_args={"encoding": "UTF-8", "nencoding": "UTF-8"}
)
SessionLocal = sessionmaker(bind=engine)

# ========================
# 4. JSON -> DB 삽입 (시퀀스 없이)
# ========================
session = SessionLocal()
try:
    with open("dummy_files.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # FILE_ID 수동 계산: 기존 최대값 + 1
    max_id = session.execute(text("SELECT NVL(MAX(FILE_ID), 0) FROM FILES")).scalar()
    count_inserted = 0

    for idx, item in enumerate(data, start=1):
        file_path = item["path"]

        if not os.path.exists(file_path):
            print(f"[경고] 파일 없음, 삽입하지 않음: {file_path}")
            continue

        # 중복 체크 (FILE_NAME 기준)
        exists = session.execute(
            text("SELECT 1 FROM FILES WHERE FILE_NAME = :fname"),
            {"fname": item["name"]}
        ).fetchone()
        if exists:
            print(f"[스킵] 이미 존재: {item['name']}")
            continue

        # DB 삽입 (시퀀스 없이 FILE_ID 수동 지정)
        session.execute(
            text("""
                INSERT INTO FILES (
                    FILE_ID, USER_ID, FILE_NAME, FILE_TYPE, FILE_DIRECTORY,
                    IS_TRANSFORM, IS_CLASSIFICATION, HIDE, CLASSIFICATION_RESULT
                ) VALUES (:id, 1001, :fname, :ftype, :fdir, 1, 1, 0, :cls)
            """),
            {
                "id": max_id + idx,
                "fname": item["name"],
                "ftype": item["type"],
                "fdir": file_path,
                "cls": item["category"]
            }
        )
        count_inserted += 1

    session.commit()
    print(f"DB 삽입 완료: {count_inserted}건")
finally:
    session.close()
