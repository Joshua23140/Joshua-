from flask import Flask, render_template, request, jsonify, session, redirect
import psycopg2
import os
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")


@app.route("/")
def home():
    return render_template("index.html")


# conexão segura
def conectar():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))


# criar tabelas
def criar_tabela():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conhecimento (
        id SERIAL PRIMARY KEY,
        pergunta TEXT UNIQUE,
        resposta TEXT
    )
    """)

    conn.commit()
    conn.close()


criar_tabela()


# registro
@app.route("/register", methods=["POST"])
def register():

    data = request.json

    if not data:
        return jsonify({"status": "erro"})

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"status": "dados incompletos"})

    senha_hash = generate_password_hash(password)

    conn = conectar()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "INSERT INTO usuarios (username, password) VALUES (%s, %s)",
            (username, senha_hash)
        )

        conn.commit()

        return jsonify({"status": "usuario criado"})

    except:
        return jsonify({"status": "usuario ja existe"})

    finally:
        conn.close()


# login
@app.route("/login", methods=["POST"])
def login():

    data = request.json

    if not data:
        return jsonify({"status": "erro"})

    username = data.get("username")
    password = data.get("password")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT password FROM usuarios WHERE username=(%s, %s)",
        (username,)
    )

    resultado = cursor.fetchone()

    conn.close()

    if resultado and check_password_hash(resultado[0], password):

        session["user"] = username

        return jsonify({"status": "logado"})

    return jsonify({"status": "erro"})


# dashboard protegido
@app.route("/dashboard")
def dashboard():

    if "user" in session:
        return f"Bem-vindo, {session['user']}"

    return redirect("/")


# logout
@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect("/")


# respostas padrão
def processar_mensagem(msg):

    msg = msg.lower()

    if "oi" in msg:
        return "Olá! Como posso ajudar?"

    if "hora" in msg:
        return str(datetime.datetime.now())

    if "nome" in msg:
        return "Sou sua IA criada em Python."

    return None


# aprender
def aprender(pergunta, resposta):

    pergunta = pergunta.strip().lower()

    conn = conectar()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "INSERT INTO conhecimento (pergunta, resposta) VALUES (?, ?)",
            (pergunta, resposta)
        )

        conn.commit()

    except:
        pass

    conn.close()


# buscar resposta
def buscar_resposta(pergunta):

    pergunta = pergunta.strip().lower()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT resposta FROM conhecimento WHERE pergunta=?",
        (pergunta,)
    )

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return resultado[0]

    return None

@app.route("/chat", methods=["POST"])
def chat():

    data = request.json

    mensagem = data.get("mensagem").lower().strip()

    # verificar se é comando de aprendizado
    if mensagem.startswith("aprender:"):

        try:

            conteudo = mensagem.replace("aprender:", "").strip()

            pergunta, resposta = conteudo.split("=", 1)

            pergunta = pergunta.strip()
            resposta = resposta.strip()

            aprender(pergunta, resposta)

            return jsonify({
                "resposta": "Aprendi com sucesso!"
            })

        except:

            return jsonify({
                "resposta": "Formato correto: aprender: pergunta = resposta"
            })

    # buscar resposta no banco
    resposta = buscar_resposta(mensagem)

    if resposta:
        return jsonify({"resposta": resposta})

    # respostas padrão
    resposta_padrao = processar_mensagem(mensagem)

    return jsonify({"resposta": resposta_padrao})



# ensinar
@app.route("/ensinar", methods=["POST"])
def ensinar():

    data = request.json

    if not data:
        return jsonify({"status": "erro"})

    pergunta = data.get("pergunta")
    resposta = data.get("resposta")

    if not pergunta or not resposta:
        return jsonify({"status": "dados incompletos"})

    aprender(pergunta, resposta)

    return jsonify({"status": "aprendido"})


# iniciar servidor
if __name__ == "__main__":
    app.run(debug=True)