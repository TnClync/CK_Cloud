from flask import Flask, jsonify, request
import time, requests, os, json
from jose import jwt
import pymysql


# =============================
# KEYCLOAK CONFIG
# =============================

ISSUER = os.getenv(
    "OIDC_ISSUER",
    "http://authentication-identity-server:8080/realms/master"
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
# DATABASE CONFIG
# =============================

DB_HOST = "relational-database-server"
DB_USER = "root"
DB_PASSWORD = "root"
DB_NAME = "minicloud"


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


@app.get("/hello")
def hello():
    return jsonify(message="Hello from App Server!")


# =============================
# SECURE API
# =============================

@app.get("/secure")
def secure():

    auth = request.headers.get("Authorization", "")

    if not auth.startswith("Bearer "):
        return jsonify(error="Missing Bearer token"), 401

    token = auth.split(" ", 1)[1]

    try:

        payload = jwt.decode(
            token,
            get_jwks(),
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
# READ JSON FILE (OLD API)
# =============================

@app.get("/student")
def student():

    try:

        BASE_DIR = os.path.dirname(__file__)
        file_path = os.path.join(BASE_DIR, "students.json")

        with open(file_path) as f:
            data = json.load(f)

        return jsonify(data)

    except Exception as e:
        return jsonify(error=str(e)), 500


# =============================
# SELECT FROM DATABASE
# =============================

@app.get("/students-db")
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
# INSERT STUDENT
# =============================

@app.post("/students-db")
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
# UPDATE STUDENT
# =============================

@app.put("/students-db/<int:id>")
def update_student(id):

    data = request.json

    conn = get_connection()

    with conn.cursor() as cursor:

        cursor.execute(
            "UPDATE students SET name=%s,email=%s WHERE id=%s",
            (data["name"], data["email"], id)
        )

        conn.commit()

    conn.close()

    return jsonify(message="Student updated")


# =============================
# DELETE STUDENT
# =============================

@app.delete("/students-db/<int:id>")
def delete_student(id):

    conn = get_connection()

    with conn.cursor() as cursor:

        cursor.execute(
            "DELETE FROM students WHERE id=%s",
            (id,)
        )

        conn.commit()

    conn.close()

    return jsonify(message="Student deleted")


# =============================
# MAIN
# =============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)