from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn, argparse
import pymysql
import pymysql.cursors

#------------------------------------------------------
# CLI arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Notes Service")
    parser.add_argument("--host", default="127.0.0.1", help="Listen host")
    parser.add_argument("--port", type=int, default=8000, help="Listen port")
    parser.add_argument("--db-host", default="127.0.0.1", help="MariaDB host")
    parser.add_argument("--db-port", type=int, default=3306, help="MariaDB port")
    parser.add_argument("--db-user", required=True, help="MariaDB user")
    parser.add_argument("--db-password", required=True, help="MariaDB password")
    parser.add_argument("--db-name", required=True, help="MariaDB database name")
    return parser.parse_args()

args = parse_args()

DB_CONFIG = {
    "host": args.db_host,
    "port": args.db_port,
    "user": args.db_user,
    "password": args.db_password,
    "database": args.db_name,
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

#----------------------------------------------------------

@app.get("/")
def read_root():
    return {
        "database_user": args.db_user
    }


#------------------------------------------------------------------
# Entry point
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
