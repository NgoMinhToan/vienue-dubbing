"""Versioned pronunciation rules and explicit per-project snapshots."""
import json
import re
from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator
from .store import Conflict


class Rule(BaseModel):
    source: str = Field(min_length=1, max_length=200)
    target: str = Field(min_length=1, max_length=500)
    whole_word: bool = True
    case_sensitive: bool = False
    enabled: bool = True

    @model_validator(mode="after")
    def nonempty(self):
        if not self.source.strip() or not self.target.strip():
            raise ValueError("Từ và cách đọc không được để trống.")
        return self


class Dictionary(BaseModel):
    version: Literal[1] = 1
    revision: int = 0
    rules: list[Rule] = Field(default_factory=list, max_length=500)


class Preview(Dictionary):
    text: str = Field(max_length=10000)


class Apply(BaseModel):
    revision: int
    dictionary_revision: int


def spoken_text(text, rules):
    # A combined regex replaces original spans once; replacement output is never re-read.
    active = [r for r in rules if r.get("enabled", True)]
    if not active:
        return text
    patterns=[]
    for i, rule in enumerate(active):
        pattern=re.escape(rule["source"])
        if rule.get("whole_word", True):
            pattern=r"(?<!\w)" + pattern + r"(?!\w)"
        if not rule.get("case_sensitive", False):
            pattern="(?i:"+pattern+")"
        patterns.append(f"(?P<r{i}>{pattern})")
    result=re.sub("|".join(patterns), lambda m: active[int(m.lastgroup[1:])]["target"], text)
    if len(result)>100000:
        raise ValueError("Văn bản sau thay thế quá dài.")
    return result


def install_dictionary(app, store, jobs):
    with store.connection() as db:
        db.execute("CREATE TABLE IF NOT EXISTS pronunciation (id INTEGER PRIMARY KEY, data TEXT NOT NULL)")

    def get():
        with store.connection() as db:
            row=db.execute("SELECT data FROM pronunciation WHERE id=1").fetchone()
        return json.loads(row[0]) if row else Dictionary().model_dump()

    router=APIRouter(prefix="/api")

    @router.get("/dictionary")
    def read():
        return get()

    @router.put("/dictionary")
    def save(values: Dictionary):
        with store.lock, store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if values.revision != get()["revision"]:
                raise Conflict("Từ điển đã thay đổi. Nạp lại trước khi lưu.")
            data=values.model_dump()
            data["revision"]+=1
            db.execute("INSERT OR REPLACE INTO pronunciation VALUES (1,?)",(json.dumps(data,ensure_ascii=False),))
        return data

    @router.post("/dictionary/preview")
    def preview(values: Preview):
        rules = [r.model_dump() for r in values.rules]
        return {"text":spoken_text(values.text, rules), "rules":rules}

    @router.post("/projects/{id}/dictionary")
    def apply(id: str, values: Apply):
        with jobs.lock, store.lock:
            p=store.get(id)
            dictionary=get()
            if values.dictionary_revision != dictionary["revision"]:
                raise Conflict("Từ điển đã đổi. Nạp lại trước khi áp dụng.")
            if any(j["project"]==id and j["status"] in ("queued","running") for j in jobs.items.values()):
                raise ValueError("Đợi hoặc dừng tác vụ trước khi áp dụng từ điển.")
            p.update(pronunciation=dictionary, revision=p["revision"]+1)
            store.save(p,expected=values.revision)
            return {"revision":p["revision"],"dictionary_revision":dictionary["revision"]}

    app.include_router(router)
    return get
