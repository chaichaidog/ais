"""ARCHIVE_001: Flask blog + server-validated puzzle.

The website keeps the puzzle answer and admin password on the server.
Use a durable PostgreSQL DATABASE_URL in production if editing posts in /admin.
"""
from __future__ import annotations

import hmac
import os
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import (
    Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
)
from sqlalchemy import (
    Boolean, Column, Integer, MetaData, String, Table, Text, create_engine, delete,
    insert, select, update
)

BASE_DIR = Path(__file__).resolve().parent
metadata = MetaData()
posts = Table(
    "posts", metadata,
    Column("id", Integer, primary_key=True),
    Column("slug", String(90), unique=True, nullable=False),
    Column("title", String(160), nullable=False),
    Column("category", String(24), nullable=False),
    Column("excerpt", String(280), nullable=False),
    Column("content", Text, nullable=False),
    Column("created_at", String(10), nullable=False),
    Column("published", Boolean, nullable=False, default=True),
)

site_meta = Table(
    "site_meta", metadata,
    Column("key", String(64), primary_key=True),
    Column("value", String(256), nullable=False),
)

SEED_POSTS = [
    {
        "slug": "first-record", "title": "最近讀到的一本小說", "category": "隨筆",
        "excerpt": "有個朋友把書裡的傳說當真了。原本以為只是開玩笑。",
        "content": "這裡本來只是普通的個人 Blog，記錄閱讀、生活和一些小作品。\n\n朋友最近迷上一部講森林儀式的小說。他說，故事裡有人可以透過獻祭換取想要的東西。\n\n他開始認真研究那片森林，還問過我願不願意一起去。當時我以為，他只是看小說看得太入迷。\n\n奇怪的是，我現在完全想不起來，是誰先提出要出發的。", "created_at": "2026-11-01", "published": True
    },
    {
        "slug": "signal-lost", "title": "森林訊號中斷紀錄", "category": "生活",
        "excerpt": "兩個人走進森林之後，手機只留下不完整的時間戳。",
        "content": "我們真的去了那片森林。帶路的人一直說，小說裡的地點就在前面。\n\n那個人原本打算拿同行者作為儀式的祭品。但儀式還沒開始，樹後就出現了兩個站姿很奇怪的人影。\n\n錄影在凌晨四點失去訊號。時間戳只剩下 04。\n\n幾天後，我們兩個都回家了。他們說我的表情變得很僵硬，連說話的習慣也不一樣。\n\n我不記得森林裡發生過什麼。至少，這是我一直告訴大家的。", "created_at": "2026-11-12", "published": True
    },
    {
        "slug": "frame-seventeen", "title": "歸來之後的第十七格", "category": "技術",
        "excerpt": "影像修復停在第 17 格。原本熟悉的行為，突然都變得陌生。",
        "content": "我試著修復進入森林那天的錄影。\n\n前十六格只有樹木和兩個人的背影。第十七格出現兩個一模一樣的身影，下一秒影片就結束了。最後保留下來的格數是 17。\n\n回來之後，我們都被問過以前的習慣：慣用手、口頭禪、喜歡的食物。奇怪的是，我們總會答錯那些原本很簡單的問題。\n\n有人說，真正走進森林的兩個人，根本沒有回來。\n\n如果這些紀錄是真的，那麼現在坐在電腦前寫字的，又是誰？", "created_at": "2026-11-18", "published": True
    },
]

VALID_CATEGORIES = {"生活", "技術", "隨筆"}
_slug_re = re.compile(r"^[a-z0-9][a-z0-9-]{1,89}$")


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", ""),
        PUZZLE_ANSWER=os.environ.get("PUZZLE_ANSWER", "0417"),
        DATABASE_URL=os.environ.get("DATABASE_URL", ""),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER_EXTERNAL_HOSTNAME")),
        MAX_CONTENT_LENGTH=100 * 1024,
        JSON_AS_ASCII=False,
    )
    if test_config:
        app.config.update(test_config)

    db_url = app.config["DATABASE_URL"]
    if not db_url:
        (BASE_DIR / "instance").mkdir(exist_ok=True)
        db_url = f"sqlite:///{BASE_DIR / 'instance' / 'blog.db'}"
    if db_url.startswith("postgres://"):
        db_url = "postgresql+psycopg://" + db_url.removeprefix("postgres://")
    elif db_url.startswith("postgresql://"):
        db_url = "postgresql+psycopg://" + db_url.removeprefix("postgresql://")
    if not re.fullmatch(r"[0-9]{4}", str(app.config["PUZZLE_ANSWER"])):
        raise ValueError("PUZZLE_ANSWER 必須是四位數字")
    engine = create_engine(db_url, pool_pre_ping=True)
    metadata.create_all(engine)
    with engine.begin() as connection:
        seeded = connection.execute(
            select(site_meta.c.value).where(site_meta.c.key == "initialized")
        ).scalar()
        if seeded is None:
            if connection.execute(select(posts.c.id).limit(1)).first() is None:
                connection.execute(insert(posts), SEED_POSTS)
            connection.execute(insert(site_meta).values(key="initialized", value="yes"))

    # Process-local throttling is intentionally lightweight. For a busy production
    # service with multiple workers, switch to a shared rate-limiter (e.g. Redis).
    attempts: dict[str, deque[float]] = defaultdict(deque)

    def limited(scope: str, max_attempts: int, seconds: int) -> bool:
        key = f"{scope}:{request.remote_addr}"
        now = time.monotonic()
        bucket = attempts[key]
        while bucket and now - bucket[0] > seconds:
            bucket.popleft()
        if len(bucket) >= max_attempts:
            return True
        bucket.append(now)
        return False

    def ensure_csrf() -> str:
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(24)
        return session["csrf"]

    def check_csrf() -> None:
        expected = session.get("csrf", "")
        supplied = request.form.get("csrf", "")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            abort(400, description="無效的表單，請重新整理後再試。")

    def admin_only(fn):
        @wraps(fn)
        def guarded(*args, **kwargs):
            if not session.get("admin"):
                return redirect(url_for("admin_login"))
            return fn(*args, **kwargs)
        return guarded

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/posts")
    def get_posts():
        with engine.connect() as connection:
            rows = connection.execute(
                select(posts).where(posts.c.published.is_(True))
                .order_by(posts.c.created_at.desc(), posts.c.id.desc())
            ).mappings().all()
        return jsonify(posts=[dict(row) for row in rows])

    @app.get("/api/posts/<slug>")
    def get_post(slug):
        with engine.connect() as connection:
            row = connection.execute(
                select(posts).where(posts.c.slug == slug, posts.c.published.is_(True))
            ).mappings().first()
        if row is None:
            return jsonify(error="檔案不存在"), 404
        return jsonify(post=dict(row))

    @app.post("/api/puzzle/verify")
    def verify_puzzle():
        if limited("puzzle", 25, 5 * 60):
            return jsonify(success=False, message="訊號過載。請稍後再試。"), 429
        if not request.is_json:
            return jsonify(success=False, message="無法辨識資料格式。"), 415
        incoming = request.get_json(silent=True)
        if not isinstance(incoming, dict) or not isinstance(incoming.get("answer"), str):
            return jsonify(success=False, message="請輸入四位數字。"), 400
        answer = incoming["answer"].strip()
        if not re.fullmatch(r"[0-9]{4}", answer):
            return jsonify(success=False, message="密碼需要四位數字。"), 400
        if not hmac.compare_digest(answer, str(app.config["PUZZLE_ANSWER"])):
            return jsonify(success=False, message="存取遭拒。錄影時間不正確。"), 200
        return jsonify(success=True, message="檔案解鎖成功。取代紀錄已恢復。")

    @app.route("/admin", methods=["GET", "POST"])
    def admin_login():
        if session.get("admin"):
            return redirect(url_for("admin_dashboard"))
        token = ensure_csrf()
        if request.method == "POST":
            check_csrf()
            if limited("admin-login", 8, 15 * 60):
                flash("登入嘗試過於頻繁，請稍後再試。", "error")
            elif not app.config["ADMIN_PASSWORD"]:
                flash("尚未設定 ADMIN_PASSWORD，後台暫時關閉。", "error")
            elif hmac.compare_digest(request.form.get("password", ""), app.config["ADMIN_PASSWORD"]):
                session.clear()
                session["admin"] = True
                ensure_csrf()
                return redirect(url_for("admin_dashboard"))
            else:
                flash("密碼錯誤。", "error")
        return render_template("login.html", csrf=token, enabled=bool(app.config["ADMIN_PASSWORD"]))

    @app.get("/admin/dashboard")
    @admin_only
    def admin_dashboard():
        with engine.connect() as connection:
            rows = connection.execute(
                select(posts).order_by(posts.c.created_at.desc(), posts.c.id.desc())
            ).mappings().all()
        return render_template(
            "dashboard.html", articles=rows, csrf=ensure_csrf(),
            transient=db_url.startswith("sqlite:"),
        )

    @app.post("/admin/logout")
    @admin_only
    def admin_logout():
        check_csrf()
        session.clear()
        return redirect(url_for("index"))

    @app.route("/admin/posts/new", methods=["GET", "POST"])
    @admin_only
    def new_post():
        return edit_post(None)

    @app.route("/admin/posts/<int:post_id>/edit", methods=["GET", "POST"])
    @admin_only
    def edit_post(post_id):
        with engine.connect() as connection:
            existing = connection.execute(select(posts).where(posts.c.id == post_id)).mappings().first() if post_id else None
        if post_id is not None and existing is None:
            abort(404)
        if request.method == "POST":
            check_csrf()
            values = {key: request.form.get(key, "").strip() for key in (
                "slug", "title", "category", "excerpt", "content", "created_at"
            )}
            values["published"] = request.form.get("published") == "on"
            valid_date = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", values["created_at"]))
            if valid_date:
                try:
                    datetime.strptime(values["created_at"], "%Y-%m-%d")
                except ValueError:
                    valid_date = False
            errors = []
            if not _slug_re.fullmatch(values["slug"]):
                errors.append("網址識別碼只能使用小寫英文字母、數字與連字號，長度 2–90。")
            if not values["title"] or len(values["title"]) > 160:
                errors.append("標題長度須為 1–160 字。")
            if values["category"] not in VALID_CATEGORIES:
                errors.append("請選擇有效分類。")
            if len(values["excerpt"]) > 280:
                errors.append("摘要不可超過 280 字。")
            if not values["content"] or len(values["content"]) > 20000:
                errors.append("文章內容須為 1–20000 字。")
            if not valid_date:
                errors.append("日期格式錯誤。")
            with engine.connect() as connection:
                conflict = connection.execute(select(posts.c.id).where(posts.c.slug == values["slug"])).scalar()
                if conflict is not None and conflict != post_id:
                    errors.append("這個網址識別碼已被使用。")
            if errors:
                for error in errors:
                    flash(error, "error")
                return render_template("editor.html", article=values, csrf=ensure_csrf(), post_id=post_id), 400
            with engine.begin() as connection:
                if post_id:
                    connection.execute(update(posts).where(posts.c.id == post_id).values(**values))
                else:
                    connection.execute(insert(posts).values(**values))
            flash("文章已儲存。", "success")
            return redirect(url_for("admin_dashboard"))
        defaults = existing or {
            "slug": "", "title": "", "category": "生活", "excerpt": "", "content": "",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "published": True
        }
        return render_template("editor.html", article=defaults, csrf=ensure_csrf(), post_id=post_id)

    @app.post("/admin/posts/<int:post_id>/delete")
    @admin_only
    def delete_post(post_id):
        check_csrf()
        with engine.begin() as connection:
            connection.execute(delete(posts).where(posts.c.id == post_id))
        flash("文章已刪除。", "success")
        return redirect(url_for("admin_dashboard"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=int(os.environ.get("PORT", "5000")))
