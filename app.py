from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
import argparse
import pymysql
import pymysql.cursors
import os

#------------------------------------------------------
# CLI arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Notes Service")
    parser.add_argument("--host", default="127.0.0.1", help="Listen host")
    parser.add_argument("--port", type=int, default=8000, help="Listen port")
    parser.add_argument("--db-host", default="127.0.0.1", help="MariaDB host")
    parser.add_argument("--db-port", type=int, default=3306, help="MariaDB port")
    parser.add_argument("--db-user", default=os.getenv('DB_USER'), help="MariaDB user")
    parser.add_argument("--db-password", default=os.getenv('DB_PASSWORD'), help="MariaDB password")
    parser.add_argument("--db-name", default=os.getenv('DB_NAME'), help="MariaDB database name")
    return parser.parse_args()

args = parse_args()

DB_CONFIG = {
    "host": args.db_host,
    "port": args.db_port,
    "user": os.getenv("DB_USER", args.db_user),
    "password": os.getenv("DB_PASSWORD", args.db_password),
    "database": os.getenv("DB_NAME", args.db_name),
    "cursorclass": pymysql.cursors.DictCursor,
    "charset": "utf8mb4",
}

#----------------------------------------------------------
# DB helpers
def get_connection():
    return pymysql.connect(**DB_CONFIG)

def db_is_ready() -> bool:
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False

#-----------------------------------------------------------
# Response helpers

def wants_html(request: Request):
    accept = request.headers.get("accept", "")
    # If client explicitly asks for html, or no preference given → html
    if "text/html" in accept:
        return True
    if "application/json" in accept:
        return False
    else:
        return True

def html_page(title: str, body: str) -> HTMLResponse:
    html = f""" <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
</head>
<body>
    <h1>{title}</h1>
    {body}
</body>
</html>"""
    return HTMLResponse(content=html)


#----------------------------------------------------------
# Health endpoints
app = FastAPI(title="Notes Service")

@app.get("/health/alive")
def health_alive():
    return HTMLResponse(content="OK", status_code=200)

@app.get("/health/ready")
def health_ready():
    if db_is_ready():
        return HTMLResponse(content="OK", status_code=200)
    return HTMLResponse(
        content="Service not ready: cannot connect to database",
        status_code=500,
    )
# ── Root ───────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def root():
    body = """
<table border="1" cellpadding="6" cellspacing="0">
  <thead>
    <tr><th>Method</th><th>Path</th><th>Description</th></tr>
  </thead>
  <tbody>
    <tr><td>GET</td><td>/notes</td><td>Список нотаток (id, title)</td></tr>
    <tr><td>POST</td><td>/notes</td><td>Створити нотатку (title, content)</td></tr>
    <tr><td>GET</td><td>/notes/{id}</td><td>Нотатка повністю (id, title, content, created_at)</td></tr>
  </tbody>
</table>"""
    return html_page("Notes Service — доступні ендпоінти", body)


#----------------------------------------------------------
# Notes endpoints
@app.get("/notes")
def list_notes(request: Request):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title FROM notes ORDER BY created_at DESC")
            rows = cur.fetchall()
            # Перевіряємо формат відповіді
        if wants_html(request):
            if not rows:
                body = "<p>Нотаток поки немає.</p>"
            else:
                # Збираємо рядки таблиці
                table_rows = ""
                for row in rows:
                    table_rows += f"<tr><td>{row['id']}</td><td>{row['title']}</td></tr>"

                body = f"""
                <table border="1" cellpadding="5" cellspacing="0">
                    <tr><th>ID</th><th>Заголовок</th></tr>
                    {table_rows}
                </table>
                """
            return html_page("Список нотаток", body)

        # Якщо не HTML, то повертаємо JSON
        return JSONResponse(content=rows)
    finally:
        conn.close()


@app.post("/notes", status_code=201)
async def create_note(request: Request):
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
        title = data.get("title", "").strip()
        content = data.get("content", "").strip()
    else:
        # form data
        form = await request.form()
        title = str(form.get("title", "")).strip()
        content = str(form.get("content", "")).strip()

    if not title or not content:
        raise HTTPException(status_code=422, detail="title and content are required")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO notes (title, content) VALUES (%s, %s)",
                (title, content),
            )
            note_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()

    if wants_html(request):
        return html_page(
            "Note Created",
            f"<p>Note created with ID: <strong>{note_id}</strong></p>"
            f'<p><a href="/notes/{note_id}">View note</a> | <a href="/notes">All notes</a></p>',
        )

    return JSONResponse(content={"id": note_id, "title": title}, status_code=201)


@app.get("/notes/{note_id}")
def get_note(note_id: int, request: Request):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, content, created_at FROM notes WHERE id = %s",
                (note_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")

    row["created_at"] = str(row["created_at"])

    if wants_html(request):
        body = f"""
<table border="1" cellpadding="6" cellspacing="0">
  <tr><th>ID</th><td>{row['id']}</td></tr>
  <tr><th>Title</th><td>{row['title']}</td></tr>
  <tr><th>Created at</th><td>{row['created_at']}</td></tr>
  <tr><th>Content</th><td>{row['content']}</td></tr>
</table>
<p><a href="/notes">Back to all notes</a></p>"""
        return html_page(f"Note #{row['id']}: {row['title']}", body)

    return JSONResponse(content=row)


#------------------------------------------------------------------
# Entry point
if __name__ == "__main__":
    import uvicorn
    listen_fds = int(os.getenv("LISTEN_FDS", "0"))
    if listen_fds >= 1:
        uvicorn.run(app, fd=3)
    else:
        uvicorn.run(app, host=args.host, port=args.port)