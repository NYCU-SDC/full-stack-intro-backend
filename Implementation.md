下面這份是可以直接放進教材的版本。整體口吻會刻意用「帶學生一步一步看懂」的方式寫，不只是丟 code。這一章的定位是：

> 我們已經知道 notes 需要哪些 RESTful endpoints，接下來要把這些 API 一支一支轉成 FastAPI + Pydantic + SQLAlchemy 的 code。

---

# Notes CRUD 實作：FastAPI + Pydantic + SQLAlchemy

---

## 本章目標

前面我們已經設計好 Digital Note 專案中 `notes` resource 需要的 RESTful API。

這一章我們要做的事情是：

> 把 API 設計轉換成真正可以執行的 backend code。

我們目前只示範 `notes` 的 CRUD，也就是建立、讀取、更新、刪除筆記。

---

## 目前的 Database Tables

我們已經在 PostgreSQL 中建立好兩張 tables：`users` 和 `notes`。

```sql
DROP TABLE IF EXISTS notes; -- 先丟掉之前建立過的 notes table
DROP TABLE IF EXISTS users; -- 先丟掉之前建立過的 users table

CREATE TABLE users (
  user_id BIGSERIAL PRIMARY KEY,       -- 指定 Primary Key
  user_name TEXT NOT NULL,             -- Constraint：不可以是 NULL
  user_email TEXT NOT NULL UNIQUE      -- Constraint：不可以是 NULL，而且必須唯一
);

CREATE TABLE notes (
  note_id BIGSERIAL PRIMARY KEY,       -- 指定 Primary Key
  user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL,         -- 標題最多 200 字，不可以是 NULL
  content TEXT NOT NULL,               -- 內容不可以是 NULL
  note_date DATE NOT NULL DEFAULT CURRENT_DATE -- 沒有給值時，預設為今天日期
);
```

這裡有幾個重點：

1. `users.user_id` 是 user 的唯一識別碼。
2. `notes.note_id` 是 note 的唯一識別碼。
3. `notes.user_id` 是 foreign key，代表這篇 note 屬於哪一個 user。
4. `ON DELETE CASCADE` 代表如果某個 user 被刪除，他底下的 notes 也會一起被刪除。
5. `note_date` 有 `DEFAULT CURRENT_DATE`，所以建立 note 時不需要手動傳入日期，PostgreSQL 會自動填入今天日期。

在這堂課中，我們會用 query parameter `user_id` 來模擬目前登入者。

例如：

```http
GET /notes?user_id=1
```

意思是：

> 取得 user_id = 1 這個使用者的所有 notes。

在真實產品中，通常不會讓 client 自己傳 `user_id`，而是從登入狀態、token 或 session 中取得 current user。這裡為了讓第一次學後端的同學先專注在 CRUD 和資料流，所以先用 query parameter 簡化。

---

# 我們要實作的 Notes API

| 功能     | Method   | Endpoint           | Query Parameters |
| ------ | -------- | ------------------ | ---------------- |
| 建立筆記   | `POST`   | `/notes`           | `user_id`        |
| 取得筆記列表 | `GET`    | `/notes`           | `user_id`        |
| 取得單篇筆記 | `GET`    | `/notes/{note_id}` | `user_id`        |
| 更新筆記   | `PATCH`  | `/notes/{note_id}` | `user_id`        |
| 刪除筆記   | `DELETE` | `/notes/{note_id}` | `user_id`        |

這五支 API 會對應到五個 CRUD 操作：

| CRUD        | API                       |
| ----------- | ------------------------- |
| Create      | `POST /notes`             |
| Read List   | `GET /notes`              |
| Read Detail | `GET /notes/{note_id}`    |
| Update      | `PATCH /notes/{note_id}`  |
| Delete      | `DELETE /notes/{note_id}` |

---

# 實作前先建立分層觀念

在開始寫每一支 API 前，我們先把後端專案拆成幾個 layer。

這樣做的目的，是避免把所有程式碼都塞進 router function 裡。

建議架構如下：

```text
app/
  main.py

  db/
    base.py
    session.py

  models/
    user.py
    note.py

  schemas/
    note.py

  services/
    note_service.py

  routers/
    notes.py
```

每一層的責任如下：

| Layer         | 檔案                         | 責任                                           |
| ------------- | -------------------------- | -------------------------------------------- |
| DB Layer      | `db/session.py`            | 建立 database connection 和 session             |
| Model Layer   | `models/note.py`           | 定義 SQLAlchemy ORM model，對應 database table    |
| Schema Layer  | `schemas/note.py`          | 定義 Pydantic schema，也就是 request / response 格式 |
| Service Layer | `services/note_service.py` | 實作真正的 CRUD 邏輯與錯誤處理                           |
| Router Layer  | `routers/notes.py`         | 定義 FastAPI endpoints                         |
| Main App      | `main.py`                  | 建立 FastAPI app，掛上 router                     |

可以先記住：

```text
FastAPI Router 負責 HTTP。
Pydantic Schema 負責資料格式。
SQLAlchemy Model 負責 database table mapping。
Service 負責真正的 business logic 和 database 操作。
```

---

# Part 1：共用基礎程式碼

在 walkthrough 五支 API 前，我們先準備共用的基礎程式碼。

---

## 1. DB Layer：建立 Base 和 Session

---

## `app/db/base.py`

```python
from sqlalchemy.orm import declarative_base

# Base 是所有 SQLAlchemy ORM models 的共同基底類別。
# 之後我們建立 User、Note model 時，都會繼承這個 Base。
Base = declarative_base()
```

### 教學重點

`Base` 可以理解成 SQLAlchemy 管理 ORM models 的起點。

之後我們寫：

```python
class Note(Base):
    ...
```

意思是：

> `Note` 是一個 SQLAlchemy ORM model，它會被 SQLAlchemy 管理，並對應到 database 中的某張 table。

---

## `app/db/session.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 這裡填入你的 PostgreSQL connection string。
# 格式：
# postgresql+psycopg2://使用者名稱:密碼@主機:port/database_name
DATABASE_URL = "postgresql+psycopg2://postgres:password@localhost:5432/digital_note"

# 建立 engine。
# engine 負責管理 Python 程式和 database 之間的底層連線。
engine = create_engine(DATABASE_URL)

# 建立 SessionLocal。
# 每一次 request 進來時，我們會建立一個新的 database session。
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,   # 不自動 commit，讓我們明確控制什麼時候寫入 database
    autoflush=False,    # 不自動 flush，初學階段比較容易理解資料何時被送出
)


def get_db():
    """
    FastAPI dependency。

    每次 request 進來時：
    1. 建立一個 db session
    2. 把 db session 提供給 router / service 使用
    3. request 結束後關閉 session
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
```

### 教學重點

`Session` 是 SQLAlchemy 和 database 溝通的工作區。

當我們要新增、查詢、更新、刪除資料時，通常都會透過 `db` 這個 session 來做。

常見操作包括：

```python
db.add(note)       # 新增資料到 session
db.commit()        # 把變更真的寫進 database
db.refresh(note)   # 從 database 重新讀取資料
db.delete(note)    # 刪除資料
```

---

# Part 2：SQLAlchemy Models

SQLAlchemy model 的任務是：

> 用 Python class 描述 database table，讓我們可以用 Python object 操作 database。

在這個專案中，我們至少需要兩個 SQLAlchemy models：

```text
User
Note
```

雖然這一章只示範 notes CRUD，但因為 `notes.user_id` 會 reference `users.user_id`，所以我們仍然需要定義 `User` model。

---

## `app/models/user.py`

```python
from sqlalchemy import BigInteger, Text, Column
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    """
    User ORM model。

    這個 class 對應到 PostgreSQL 裡的 users table。
    一個 User object 代表 users table 裡的一筆資料。
    """

    __tablename__ = "users"

    # 對應 users.user_id
    # user_id 是 Primary Key，由 PostgreSQL 的 BIGSERIAL 自動產生。
    user_id = Column(BigInteger, primary_key=True, index=True)

    # 對應 users.user_name
    # nullable=False 對應 SQL 裡的 NOT NULL。
    user_name = Column(Text, nullable=False)

    # 對應 users.user_email
    # nullable=False 對應 NOT NULL。
    # unique=True 對應 UNIQUE constraint。
    user_email = Column(Text, nullable=False, unique=True)

    # relationship 用來描述 User 和 Note 的關係。
    # 一個 user 可以有很多 notes。
    notes = relationship(
        "Note",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
```

---

## `app/models/note.py`

```python
from sqlalchemy import BigInteger, Text, String, Date, Column, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class Note(Base):
    """
    Note ORM model。

    這個 class 對應到 PostgreSQL 裡的 notes table。
    一個 Note object 代表 notes table 裡的一筆資料。
    """

    __tablename__ = "notes"

    # 對應 notes.note_id
    # note_id 是 Primary Key，由 PostgreSQL 的 BIGSERIAL 自動產生。
    note_id = Column(BigInteger, primary_key=True, index=True)

    # 對應 notes.user_id
    # ForeignKey("users.user_id") 表示這個欄位會參考 users table 的 user_id。
    # ondelete="CASCADE" 對應 SQL 裡的 ON DELETE CASCADE。
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 對應 notes.title
    # PostgreSQL 中是 VARCHAR(200)，所以 SQLAlchemy 使用 String(200)。
    title = Column(String(200), nullable=False)

    # 對應 notes.content
    # PostgreSQL 中是 TEXT，所以 SQLAlchemy 使用 Text。
    content = Column(Text, nullable=False)

    # 對應 notes.note_date
    # database 已經設定 DEFAULT CURRENT_DATE。
    # 建立 note 時不需要手動指定，PostgreSQL 會自動給值。
    note_date = Column(Date, nullable=False)

    # relationship 用來描述 Note 和 User 的關係。
    # 多篇 notes 屬於同一個 user。
    owner = relationship(
        "User",
        back_populates="notes",
    )
```

---

## 小結：SQLAlchemy Model 和 Database Table 的關係

在這個案例中，對應關係如下：

| PostgreSQL Table / Column | SQLAlchemy Model / Attribute |
| ------------------------- | ---------------------------- |
| `users`                   | `User`                       |
| `notes`                   | `Note`                       |
| `users.user_id`           | `User.user_id`               |
| `notes.note_id`           | `Note.note_id`               |
| `notes.user_id`           | `Note.user_id`               |
| `notes.title`             | `Note.title`                 |
| `notes.content`           | `Note.content`               |
| `notes.note_date`         | `Note.note_date`             |

要注意：

> SQLAlchemy model 不是另一個 database。
> 它是 Python 端對 database table 的描述，讓我們可以用 Python 操作 PostgreSQL。

---

# Part 3：Pydantic Schemas

SQLAlchemy model 是 backend 和 database 溝通用的。
Pydantic schema 是 backend 和 client 溝通用的。

也就是說：

```text
SQLAlchemy Model：backend ↔ database
Pydantic Schema：client ↔ backend
```

我們這次 notes CRUD 需要四個 Pydantic schemas：

```text
NoteCreate
NoteRead
NoteUpdate
NoteListResponse
```

---

## `app/schemas/note.py`

```python
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    """
    POST /notes 的 request body。

    client 建立 note 時，只需要傳 title 和 content。
    不需要傳 note_id，因為 note_id 由 PostgreSQL 的 BIGSERIAL 自動產生。
    不需要傳 user_id，因為這堂課用 query parameter 模擬目前登入者。
    不需要傳 note_date，因為 note_date 由 PostgreSQL 的 DEFAULT CURRENT_DATE 自動產生。
    """

    title: str = Field(
        min_length=1,
        max_length=200,
        description="筆記標題，長度需介於 1 到 200 之間",
    )

    content: str = Field(
        min_length=1,
        description="筆記內容，不可為空",
    )


class NoteRead(BaseModel):
    """
    server 回傳 note 時使用的 response schema。

    用於：
    - POST /notes
    - GET /notes/{note_id}
    - PATCH /notes/{note_id}

    這裡定義的是 client 會看到的 note 格式。
    """

    note_id: int
    user_id: int
    title: str
    content: str
    note_date: date

    # Pydantic v2 設定：
    # 讓 Pydantic 可以從 SQLAlchemy ORM object 讀取欄位。
    #
    # 如果沒有這個設定，FastAPI 回傳 SQLAlchemy object 時，
    # Pydantic 可能不知道要如何把 ORM object 轉成 response schema。
    model_config = ConfigDict(from_attributes=True)


class NoteUpdate(BaseModel):
    """
    PATCH /notes/{note_id} 的 request body。

    PATCH 代表 partial update。
    也就是 client 可以只傳想修改的欄位。

    例如：
    {
      "title": "Updated Title"
    }

    或：
    {
      "content": "Updated content"
    }

    所以這裡的 title 和 content 都是 optional。
    """

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="新的筆記標題",
    )

    content: str | None = Field(
        default=None,
        min_length=1,
        description="新的筆記內容",
    )


class NoteListResponse(BaseModel):
    """
    GET /notes 的 response body。

    因為 GET /notes 回傳的是多篇 notes，
    所以外層用 items 包起來。

    Example:
    {
      "items": [
        {
          "note_id": 101,
          "user_id": 1,
          "title": "API Design",
          "content": "...",
          "note_date": "2026-04-29"
        }
      ]
    }
    """

    items: list[NoteRead]
```

---

## 為什麼需要不同 Schema？

| Schema             | 用途                      | 對應 API                                                          |
| ------------------ | ----------------------- | --------------------------------------------------------------- |
| `NoteCreate`       | 建立 note 時 client 可以傳的資料 | `POST /notes`                                                   |
| `NoteRead`         | server 回傳 note 時的格式     | `POST /notes`, `GET /notes/{note_id}`, `PATCH /notes/{note_id}` |
| `NoteUpdate`       | 更新 note 時 client 可以傳的資料 | `PATCH /notes/{note_id}`                                        |
| `NoteListResponse` | 回傳 note list 的格式        | `GET /notes`                                                    |

這裡要特別記住：

> `Note` 是 SQLAlchemy ORM model，對應 database。
> `NoteCreate`、`NoteRead`、`NoteUpdate` 是 Pydantic schemas，對應 API request / response。

它們名字很像，但責任不同。

---

# Part 4：Service Layer

Service layer 是真正處理 CRUD 邏輯的地方。

Router 不應該直接塞滿 database query。
Router 應該只負責 HTTP。
Service 則負責實際的資料操作、錯誤處理與商業規則。

在這個案例中，service 會負責：

1. 檢查 user 是否存在
2. 檢查 note 是否存在
3. 檢查 note 是否屬於指定 user
4. 建立 note
5. 查詢 notes
6. 更新 note
7. 刪除 note

---

## `app/services/note_service.py`

```python
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.note import Note
from app.models.user import User
from app.schemas.note import NoteCreate, NoteUpdate


def get_user_or_404(db: Session, user_id: int) -> User:
    """
    根據 user_id 查詢 user。

    為什麼需要這個 function？
    因為我們建立 note 時，需要確認這個 user 真的存在。
    如果 user 不存在，就不應該讓他建立 note。

    如果查不到 user，就回 404 Not Found。
    """

    user = db.query(User).filter(User.user_id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


def get_note_or_404(db: Session, note_id: int, user_id: int) -> Note:
    """
    根據 note_id 和 user_id 查詢 note。

    這裡非常重要：
    我們不是只用 note_id 查 note，
    而是同時檢查 user_id。

    原因是：
    即使 note_id 存在，也不代表目前這個 user 有權限讀取或修改它。

    所以查詢條件必須包含：
    - Note.note_id == note_id
    - Note.user_id == user_id
    """

    note = (
        db.query(Note)
        .filter(
            Note.note_id == note_id,
            Note.user_id == user_id,
        )
        .first()
    )

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    return note


def create_note(db: Session, user_id: int, payload: NoteCreate) -> Note:
    """
    建立一篇新的 note。

    對應 API：
    POST /notes?user_id=1

    這裡的 payload 是 NoteCreate，
    代表 request body 已經通過 Pydantic validation。
    """

    # Step 1：確認 user 存在
    get_user_or_404(db, user_id)

    # Step 2：建立 SQLAlchemy Note object
    #
    # note_id 不需要手動給，因為 PostgreSQL 會用 BIGSERIAL 自動產生。
    # note_date 不需要手動給，因為 PostgreSQL 會用 DEFAULT CURRENT_DATE 自動產生。
    note = Note(
        user_id=user_id,
        title=payload.title,
        content=payload.content,
    )

    # Step 3：把 note 加入目前的 database session
    db.add(note)

    # Step 4：commit 後，資料才會真的寫入 PostgreSQL
    db.commit()

    # Step 5：refresh 會從 database 重新讀取這筆 note
    # 這樣才能取得 note_id、note_date 這些由 database 產生的值。
    db.refresh(note)

    return note


def list_notes(db: Session, user_id: int) -> list[Note]:
    """
    取得某個 user 的所有 notes。

    對應 API：
    GET /notes?user_id=1
    """

    # Step 1：確認 user 存在
    get_user_or_404(db, user_id)

    # Step 2：查詢這個 user 的所有 notes
    #
    # 注意：
    # 不可以直接查詢所有 notes。
    # 否則 user 可能會看到別人的 notes。
    notes = (
        db.query(Note)
        .filter(Note.user_id == user_id)
        .order_by(Note.note_id.desc())
        .all()
    )

    return notes


def get_note(db: Session, note_id: int, user_id: int) -> Note:
    """
    取得單篇 note。

    對應 API：
    GET /notes/{note_id}?user_id=1
    """

    return get_note_or_404(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )


def update_note(
    db: Session,
    note_id: int,
    user_id: int,
    payload: NoteUpdate,
) -> Note:
    """
    更新一篇 note。

    對應 API：
    PATCH /notes/{note_id}?user_id=1

    PATCH 是 partial update。
    也就是 client 可以只傳想修改的欄位。
    """

    # Step 1：先找到 note
    # 如果 note 不存在，或 note 不屬於這個 user，就會回 404。
    note = get_note_or_404(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    # Step 2：只取出 client 真的有傳的欄位
    #
    # Pydantic v2 使用 model_dump(exclude_unset=True)。
    # exclude_unset=True 的意思是：
    # 沒有出現在 request body 裡的欄位，不要放進 update_data。
    update_data = payload.model_dump(exclude_unset=True)

    # Step 3：如果 client 沒有傳任何欄位，就沒有東西可以更新。
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    # Step 4：逐一更新欄位
    #
    # 如果 update_data 是 {"title": "Updated Title"}，
    # 就只會更新 note.title。
    #
    # 如果 update_data 是 {"content": "Updated content"}，
    # 就只會更新 note.content。
    for field, value in update_data.items():
        setattr(note, field, value)

    # Step 5：把修改後的 note 加回 session
    db.add(note)

    # Step 6：commit 後才會真的更新 database
    db.commit()

    # Step 7：refresh 後取得 database 中最新狀態
    db.refresh(note)

    return note


def delete_note(db: Session, note_id: int, user_id: int) -> None:
    """
    刪除一篇 note。

    對應 API：
    DELETE /notes/{note_id}?user_id=1
    """

    # Step 1：先找到 note
    # 如果 note 不存在，或 note 不屬於這個 user，就會回 404。
    note = get_note_or_404(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    # Step 2：刪除 note
    db.delete(note)

    # Step 3：commit 後才會真的從 database 刪除
    db.commit()
```

---

# Part 5：Router Layer

Router layer 負責定義 FastAPI endpoints。

Router 主要負責：

1. Method
2. Path
3. Query parameters
4. Path parameters
5. Request body
6. Response model
7. Status code
8. 呼叫 service

Router 不應該負責大量 database query。
這樣可以讓 router 保持簡單，也讓 service logic 比較容易測試和重用。

---

## `app/routers/notes.py`

```python
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate, NoteListResponse
from app.services import note_service


router = APIRouter(
    prefix="/notes",
    tags=["notes"],
)


@router.post(
    "",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
)
def create_note(
    payload: NoteCreate,
    user_id: int = Query(..., description="模擬目前登入者 ID"),
    db: Session = Depends(get_db),
):
    """
    建立筆記。

    對應 API：
    POST /notes?user_id=1
    """

    return note_service.create_note(
        db=db,
        user_id=user_id,
        payload=payload,
    )


@router.get(
    "",
    response_model=NoteListResponse,
)
def list_notes(
    user_id: int = Query(..., description="模擬目前登入者 ID"),
    db: Session = Depends(get_db),
):
    """
    取得某個 user 的所有 notes。

    對應 API：
    GET /notes?user_id=1
    """

    notes = note_service.list_notes(
        db=db,
        user_id=user_id,
    )

    return NoteListResponse(items=notes)


@router.get(
    "/{note_id}",
    response_model=NoteRead,
)
def get_note(
    note_id: int,
    user_id: int = Query(..., description="模擬目前登入者 ID"),
    db: Session = Depends(get_db),
):
    """
    取得單篇筆記。

    對應 API：
    GET /notes/{note_id}?user_id=1
    """

    return note_service.get_note(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )


@router.patch(
    "/{note_id}",
    response_model=NoteRead,
)
def update_note(
    note_id: int,
    payload: NoteUpdate,
    user_id: int = Query(..., description="模擬目前登入者 ID"),
    db: Session = Depends(get_db),
):
    """
    更新筆記。

    對應 API：
    PATCH /notes/{note_id}?user_id=1
    """

    return note_service.update_note(
        db=db,
        note_id=note_id,
        user_id=user_id,
        payload=payload,
    )


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_note(
    note_id: int,
    user_id: int = Query(..., description="模擬目前登入者 ID"),
    db: Session = Depends(get_db),
):
    """
    刪除筆記。

    對應 API：
    DELETE /notes/{note_id}?user_id=1
    """

    note_service.delete_note(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    # 204 No Content 不應該回傳 response body。
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

---

# Part 6：Main App

最後要把 notes router 掛到 FastAPI app 上。

---

## `app/main.py`

```python
from fastapi import FastAPI

from app.routers import notes


app = FastAPI(
    title="Digital Note API",
    description="A simple Digital Note API for teaching RESTful API design.",
)


# 掛上 notes router。
# 之後所有 /notes 開頭的 API 都會由 notes.router 處理。
app.include_router(notes.router)
```

---

# Code Walkthrough 1：建立筆記

---

## API Spec

| 項目               | 內容                 |
| ---------------- | ------------------ |
| Method           | `POST`             |
| Path             | `/notes`           |
| Query Parameters | `user_id`          |
| Request Body     | `title`, `content` |
| Success Status   | `201 Created`      |

---

## Example Request

```http
POST /notes?user_id=1
Content-Type: application/json
```

```json
{
  "title": "API Design",
  "content": "RESTful API should use resources and HTTP methods."
}
```

---

## Step 1：Pydantic 負責驗證 Request Body

```python
class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
```

這段代表：

> client 建立 note 時，必須傳入 `title` 和 `content`。
> `title` 長度必須介於 1 到 200。
> `content` 不可以是空字串。

如果 client 沒有傳 `title`，或者 `title` 超過 200 字，FastAPI / Pydantic 會在資料進入 service 前先擋下來。

---

## Step 2：SQLAlchemy 負責建立 Database Object

```python
note = Note(
    user_id=user_id,
    title=payload.title,
    content=payload.content,
)
```

這裡的 `Note` 是 SQLAlchemy ORM model。

它對應的是 `notes` table。

注意：

```text
note_id 不需要手動指定。
note_date 不需要手動指定。
```

因為：

```sql
note_id BIGSERIAL PRIMARY KEY
note_date DATE NOT NULL DEFAULT CURRENT_DATE
```

這兩個欄位會由 PostgreSQL 自動產生。

---

## Step 3：Service 負責真正寫入 Database

```python
def create_note(db: Session, user_id: int, payload: NoteCreate) -> Note:
    get_user_or_404(db, user_id)

    note = Note(
        user_id=user_id,
        title=payload.title,
        content=payload.content,
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    return note
```

這段流程是：

1. 先確認 `user_id` 對應的 user 存在
2. 建立一個 `Note` object
3. 用 `db.add(note)` 把它加入 session
4. 用 `db.commit()` 寫入 database
5. 用 `db.refresh(note)` 取得 database 產生的 `note_id` 和 `note_date`
6. 回傳建立好的 note

---

## Step 4：FastAPI Router 負責接 HTTP Request

```python
@router.post("", response_model=NoteRead, status_code=201)
def create_note(
    payload: NoteCreate,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    return note_service.create_note(db, user_id, payload)
```

這段 router 表示：

* `POST /notes`
* request body 要符合 `NoteCreate`
* query parameter 要有 `user_id`
* 成功時回 `201 Created`
* response body 使用 `NoteRead`
* 真正建立資料的邏輯交給 `note_service.create_note()`

---

# Code Walkthrough 2：取得筆記列表

---

## API Spec

| 項目               | 內容        |
| ---------------- | --------- |
| Method           | `GET`     |
| Path             | `/notes`  |
| Query Parameters | `user_id` |
| Success Status   | `200 OK`  |

---

## Example Request

```http
GET /notes?user_id=1
```

---

## Example Response

```json
{
  "items": [
    {
      "note_id": 101,
      "user_id": 1,
      "title": "API Design",
      "content": "RESTful API should use resources and HTTP methods.",
      "note_date": "2026-04-29"
    }
  ]
}
```

---

## Step 1：Pydantic 定義 List Response

```python
class NoteListResponse(BaseModel):
    items: list[NoteRead]
```

`GET /notes` 回傳的是多篇 notes，所以外層用 `items` 包起來。

這樣 response shape 會比較穩定：

```json
{
  "items": []
}
```

即使目前沒有任何 notes，也可以回傳：

```json
{
  "items": []
}
```

---

## Step 2：SQLAlchemy 查詢這個 User 的 Notes

```python
notes = (
    db.query(Note)
    .filter(Note.user_id == user_id)
    .order_by(Note.note_id.desc())
    .all()
)
```

這段的重點是：

> 我們只查 `Note.user_id == user_id` 的 notes。

不應該直接查：

```python
db.query(Note).all()
```

因為那樣會把所有 users 的 notes 都查出來。

在真實產品中，這會變成嚴重的資料權限問題。

---

## Step 3：Service 負責 List Logic

```python
def list_notes(db: Session, user_id: int) -> list[Note]:
    get_user_or_404(db, user_id)

    notes = (
        db.query(Note)
        .filter(Note.user_id == user_id)
        .order_by(Note.note_id.desc())
        .all()
    )

    return notes
```

這段流程是：

1. 先確認 user 存在
2. 查詢該 user 的所有 notes
3. 依照 `note_id` 由大到小排序
4. 回傳 notes list

---

## Step 4：FastAPI Router 回傳 NoteListResponse

```python
@router.get("", response_model=NoteListResponse)
def list_notes(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    notes = note_service.list_notes(db, user_id)
    return NoteListResponse(items=notes)
```

這段 router 表示：

* `GET /notes`
* query parameter 必須有 `user_id`
* response body 會符合 `NoteListResponse`
* 真正查詢 notes 的邏輯交給 `note_service.list_notes()`

---

# Code Walkthrough 3：取得單篇筆記

---

## API Spec

| 項目               | 內容                 |
| ---------------- | ------------------ |
| Method           | `GET`              |
| Path             | `/notes/{note_id}` |
| Path Parameters  | `note_id`          |
| Query Parameters | `user_id`          |
| Success Status   | `200 OK`           |

---

## Example Request

```http
GET /notes/101?user_id=1
```

---

## Step 1：FastAPI 解析 Path Parameter 和 Query Parameter

```python
@router.get("/{note_id}", response_model=NoteRead)
def get_note(
    note_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    return note_service.get_note(db, note_id, user_id)
```

這裡有兩種參數：

| 參數        | 來源              | 說明                            |
| --------- | --------------- | ----------------------------- |
| `note_id` | path parameter  | `/notes/{note_id}` 中的 note_id |
| `user_id` | query parameter | `?user_id=1`                  |

---

## Step 2：SQLAlchemy 同時檢查 note_id 和 user_id

```python
note = (
    db.query(Note)
    .filter(
        Note.note_id == note_id,
        Note.user_id == user_id,
    )
    .first()
)
```

這裡不能只用 `note_id` 查。

不建議：

```python
db.query(Note).filter(Note.note_id == note_id).first()
```

因為：

> note_id 存在，不代表這篇 note 屬於目前這個 user。

正確做法是同時檢查：

```text
note_id 是否正確
user_id 是否正確
```

這樣才能確保使用者只能取得自己的 note。

---

## Step 3：Service 負責找不到時回 404

```python
def get_note_or_404(db: Session, note_id: int, user_id: int) -> Note:
    note = (
        db.query(Note)
        .filter(
            Note.note_id == note_id,
            Note.user_id == user_id,
        )
        .first()
    )

    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    return note
```

這裡的設計是：

> 如果 note 不存在，或 note 不屬於這個 user，都回 `404 Not Found`。

這樣可以避免透露其他 user 的 note 是否存在。

---

# Code Walkthrough 4：更新筆記

---

## API Spec

| 項目               | 內容                            |
| ---------------- | ----------------------------- |
| Method           | `PATCH`                       |
| Path             | `/notes/{note_id}`            |
| Path Parameters  | `note_id`                     |
| Query Parameters | `user_id`                     |
| Request Body     | `title`, `content`，都 optional |
| Success Status   | `200 OK`                      |

---

## Example Request

```http
PATCH /notes/101?user_id=1
Content-Type: application/json
```

```json
{
  "title": "Updated Title"
}
```

---

## Step 1：Pydantic 定義 Update Schema

```python
class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
```

這裡和 `NoteCreate` 不一樣。

`NoteCreate` 代表建立 note，所以 `title` 和 `content` 都是必填。

但 `NoteUpdate` 用在 `PATCH`。

`PATCH` 是 partial update，所以 client 可以只傳想改的欄位。

例如只改 title：

```json
{
  "title": "Updated Title"
}
```

只改 content：

```json
{
  "content": "Updated content"
}
```

所以 `title` 和 `content` 都要設成 optional。

---

## Step 2：取得 Client 真的有傳的欄位

```python
update_data = payload.model_dump(exclude_unset=True)
```

這行非常重要。

`exclude_unset=True` 的意思是：

> 只取出 request body 中真的有出現的欄位。

假設 client 傳：

```json
{
  "title": "Updated Title"
}
```

那 `update_data` 會是：

```python
{
    "title": "Updated Title"
}
```

它不會包含 `content`。

這樣我們就不會誤把 `content` 更新成 `None`。

---

## Step 3：Service 逐一更新欄位

```python
for field, value in update_data.items():
    setattr(note, field, value)
```

這段 code 的意思是：

> 對 client 有傳的每一個欄位，把 note 物件上的對應欄位改成新的值。

例如：

```python
setattr(note, "title", "Updated Title")
```

等同於：

```python
note.title = "Updated Title"
```

---

## Step 4：完整 Update Service

```python
def update_note(
    db: Session,
    note_id: int,
    user_id: int,
    payload: NoteUpdate,
) -> Note:
    note = get_note_or_404(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    for field, value in update_data.items():
        setattr(note, field, value)

    db.add(note)
    db.commit()
    db.refresh(note)

    return note
```

這段流程是：

1. 先找到這篇 note
2. 確認 note 屬於這個 user
3. 取出 client 有傳的欄位
4. 如果沒有任何欄位，就回 `400 Bad Request`
5. 更新欄位
6. commit 寫入 database
7. refresh 取得最新資料
8. 回傳更新後的 note

---

## Step 5：FastAPI Router

```python
@router.patch("/{note_id}", response_model=NoteRead)
def update_note(
    note_id: int,
    payload: NoteUpdate,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    return note_service.update_note(db, note_id, user_id, payload)
```

這段 router 表示：

* `PATCH /notes/{note_id}`
* path parameter 是 `note_id`
* query parameter 是 `user_id`
* request body 是 `NoteUpdate`
* response body 是 `NoteRead`
* 真正更新資料的邏輯交給 service

---

# Code Walkthrough 5：刪除筆記

---

## API Spec

| 項目               | 內容                 |
| ---------------- | ------------------ |
| Method           | `DELETE`           |
| Path             | `/notes/{note_id}` |
| Path Parameters  | `note_id`          |
| Query Parameters | `user_id`          |
| Success Status   | `204 No Content`   |

---

## Example Request

```http
DELETE /notes/101?user_id=1
```

---

## Step 1：刪除前一樣要先查詢

```python
note = get_note_or_404(db, note_id, user_id)
```

刪除前不能直接刪：

```python
db.query(Note).filter(Note.note_id == note_id).delete()
```

因為這樣沒有檢查這篇 note 是否屬於目前 user。

我們仍然要先確認：

1. note 存在
2. note 屬於這個 user

---

## Step 2：SQLAlchemy 刪除資料

```python
db.delete(note)
db.commit()
```

這兩行代表：

| Code              | 意思                 |
| ----------------- | ------------------ |
| `db.delete(note)` | 標記這個 note 要被刪除     |
| `db.commit()`     | 真的把刪除操作寫入 database |

---

## Step 3：完整 Delete Service

```python
def delete_note(db: Session, note_id: int, user_id: int) -> None:
    note = get_note_or_404(
        db=db,
        note_id=note_id,
        user_id=user_id,
    )

    db.delete(note)
    db.commit()
```

這個 function 不需要回傳 note。

原因是：

> 刪除成功後，我們只需要告訴 client：刪除成功。

---

## Step 4：FastAPI Router 回傳 204

```python
@router.delete("/{note_id}", status_code=204)
def delete_note(
    note_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    note_service.delete_note(db, note_id, user_id)
    return Response(status_code=204)
```

這裡使用：

```http
204 No Content
```

代表：

> 操作成功，但 response body 沒有內容。

所以 `DELETE` 成功後不需要回傳 JSON。

---

# 五支 API 的總整理

| 功能   | Pydantic Schema          | SQLAlchemy Model | Service Function | Router                    |
| ---- | ------------------------ | ---------------- | ---------------- | ------------------------- |
| 建立筆記 | `NoteCreate`, `NoteRead` | `Note`           | `create_note()`  | `POST /notes`             |
| 取得列表 | `NoteListResponse`       | `Note`           | `list_notes()`   | `GET /notes`              |
| 取得單篇 | `NoteRead`               | `Note`           | `get_note()`     | `GET /notes/{note_id}`    |
| 更新筆記 | `NoteUpdate`, `NoteRead` | `Note`           | `update_note()`  | `PATCH /notes/{note_id}`  |
| 刪除筆記 | 無 response body          | `Note`           | `delete_note()`  | `DELETE /notes/{note_id}` |

---

# 本章總結

這一章我們把 notes 的五支 RESTful API 實作出來。

最重要的不是背每一行 code，而是理解每一層的責任。

```text
FastAPI Router
負責 HTTP endpoint。

Pydantic Schema
負責 request / response 的資料格式與 validation。

SQLAlchemy Model
負責對應 database table。

Service Layer
負責真正的 CRUD 邏輯、查詢和錯誤處理。

PostgreSQL
負責真正儲存資料與保證資料限制。
```

因此，寫 API 時不要把所有東西都塞進 router。

比較好的流程是：

```text
API Spec
  ↓
Pydantic Schemas
  ↓
SQLAlchemy Models
  ↓
Service Functions
  ↓
FastAPI Routers
  ↓
Complete CRUD API
```

最後要記住：

> `NoteCreate` 是 client 建立 note 時可以傳的資料。
> `NoteRead` 是 server 回傳 note 時的資料格式。
> `NoteUpdate` 是 client 更新 note 時可以傳的資料。
> `Note` 是 SQLAlchemy ORM model，對應 PostgreSQL 的 `notes` table。
> Router 負責 HTTP，Service 負責邏輯，Model 負責 database mapping，Schema 負責 API contract。
