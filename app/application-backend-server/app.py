from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from flask import Flask, jsonify, request
import time, requests, os, json
from jose import jwt
import pymysql
from flask_cors import CORS
from datetime import datetime

# =============================
# KEYCLOAK CONFIG
# =============================

ISSUER = os.getenv(
    "OIDC_ISSUER",
    "http://18.136.123.73:8081/realms/realm_sv512h0156_sv523h0191"
)

AUDIENCE = os.getenv("OIDC_AUDIENCE", "myapp")

JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"

_JWKS = None
_TS = 0


def get_jwks():
    global _JWKS, _TS
    now = time.time()

    if not _JWKS or now - _TS > 600:
        _JWKS = requests.get(JWKS_URL, timeout=5).json()
        _TS = now

    return _JWKS


# =============================
# GET RSA KEY FROM JWKS (FIX CORE BUG)
# =============================

def get_public_key(token):
    header = jwt.get_unverified_header(token)
    kid = header["kid"]

    jwks = get_jwks()

    for key in jwks["keys"]:
        if key["kid"] == kid:
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }

    raise Exception("Public key not found in JWKS")


# =============================
# DATABASE CONFIG
# =============================

DB_HOST = "relational-database-server"
DB_USER = "root"
DB_PASSWORD = "root"
DB_NAME = "studentdb"


def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )


# =============================
# FLASK APP
# =============================

app = Flask(__name__)
CORS(app)
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "endpoint", "status"]
)


@app.after_request
def track_requests(response):
    REQUEST_COUNT.labels(
        request.method,
        request.path,
        str(response.status_code)
    ).inc()

    return response


# =============================
# HEALTH API
# =============================

@app.get("/hello")
def hello():
    return jsonify(message="Hello from App Server!")


# =============================
# SECURE API (FIXED JWT VERIFY)
# =============================

@app.get("/secure")
def secure():

    auth = request.headers.get("Authorization", "")

    if not auth.startswith("Bearer "):
        return jsonify(error="Missing Bearer token"), 401

    token = auth.split(" ", 1)[1]

    try:
        key = get_public_key(token)

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER
        )

        return jsonify(
            message="Secure resource OK",
            preferred_username=payload.get("preferred_username")
        )

    except Exception as e:
        return jsonify(error=str(e)), 401


# =============================
# READ JSON FILE
# =============================

@app.get("/api/student")
def student():
    try:
        base_dir = os.path.dirname(__file__)
        file_path = os.path.join(base_dir, "students.json")

        with open(file_path) as f:
            data = json.load(f)

        return jsonify(data)

    except Exception as e:
        return jsonify(error=str(e)), 500


# =============================
# SELECT DB
# =============================

@app.get("/api/students-db")
def students_db():
    try:
        conn = get_connection()

        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM students")
            result = cursor.fetchall()

        conn.close()
        return jsonify(result)

    except Exception as e:
        return jsonify(error=str(e)), 500


# =============================
# INSERT
# =============================

@app.post("/api/students-db")
def add_student():
    data = request.json

    conn = get_connection()

    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO students(student_id, fullname, dob, major)
            VALUES (%s,%s,%s,%s)
            """,
            (
                data["student_id"],
                data["fullname"],
                data["dob"],
                data["major"]
            )
        )
        conn.commit()

    conn.close()
    return jsonify(message="Student added")


# =============================
# UPDATE (FIXED)
# =============================

@app.put("/api/students-db/<int:id>")
def update_student(id):
    data = request.json

    conn = get_connection()

    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE students 
            SET student_id=%s, fullname=%s, dob=%s, major=%s 
            WHERE id=%s
            """,
            (
                data["student_id"],
                data["fullname"],
                data["dob"],
                data["major"],
                id
            )
        )
        conn.commit()

    conn.close()
    return jsonify(message="Student updated")


# =============================
# DELETE
# =============================

@app.delete("/api/students-db/<int:id>")
def delete_student(id):
    conn = get_connection()

    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM students WHERE id=%s", (id,))
        conn.commit()

    conn.close()
    return jsonify(message="Student deleted", id=id)


# =============================
# METRICS
# =============================

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {
        "Content-Type": CONTENT_TYPE_LATEST
    }


# =============================
# RUN
# =============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)