from flask import Flask, render_template, request, jsonify, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import datetime
import numpy as np
import psycopg2
import os

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "chave_local_dev")

cliente = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversas (
        id SERIAL PRIMARY KEY,
        usuario TEXT,
        mensagem TEXT,
        resposta TEXT,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        "SELECT password FROM usuarios WHERE username=%s",
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
            "INSERT INTO conhecimento (pergunta, resposta) VALUES (%s, %s)",
            (pergunta, resposta)
        )

        conn.commit()

    except:
        pass

    conn.close()


# buscar resposta
def buscar_contexto(pergunta):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT pergunta, resposta FROM conhecimento"
    )

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return ""

    vetor_pergunta = modelo.encode(pergunta)

    melhores = []

    for p, r in dados:

        vetor_bd = modelo.encode(p)

        score = similaridade(vetor_pergunta, vetor_bd)

        melhores.append((score, p, r))

    melhores.sort(reverse=True)

    contexto = ""

    for score, p, r in melhores[:3]:
        contexto += f"Pergunta: {p}\nResposta: {r}\n\n"

    return contexto

def salvar_conversa(usuario, mensagem, resposta):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO conversas (usuario, mensagem, resposta) VALUES (%s, %s, %s)",
        (usuario, mensagem, resposta)
    )

    conn.commit()
    cursor.close()
    conn.close()

@app.route("/chat", methods=["POST"])
def chat():
    if "user" not in session:
        return jsonify({"resposta": "Faça login primeiro."})
   
    data = request.json
    mensagem = data.get("mensagem")
    resposta = gerar_resposta_rag(mensagem)
    if not resposta:
        resposta = gerar_resposta_ia(mensagem)
    salvar_conversa(session["user"], mensagem, resposta)
    return jsonify({"resposta": resposta})
    mensagem = data.get("mensagem")

    if not mensagem:
       return jsonify({"resposta": "Mensagem vazia"})


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

@app.route("/historico")
def historico():

    if "user" not in session:
        return redirect("/")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT mensagem, resposta, data FROM conversas WHERE usuario=%s ORDER BY data DESC",
        (session["user"],)
    )

    dados = cursor.fetchall()

    conn.close()

    return jsonify(dados)

modelo = None

def get_model():
    global modelo
    if modelo is None:
        from sentence_transformers import SentenceTransformer
        modelo = SentenceTransformer("all-MiniLM-L6-v2")
    return modelo

def similaridade(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def gerar_resposta_ia(pergunta):

    resposta = cliente.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Você é um assistente útil em um site."},
            {"role": "user", "content": pergunta}
        ]
    )

    return resposta.choices[0].message.content

def gerar_resposta_rag(pergunta):

    contexto = buscar_contexto(pergunta)

    prompt = f"""
Use as informações abaixo para responder a pergunta do usuário.

{contexto}

Pergunta do usuário:
{pergunta}
"""

    resposta = cliente.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Você responde baseado no conhecimento fornecido."},
            {"role": "user", "content": prompt}
        ]
    )

    return resposta.choices[0].message.content

# iniciar servidor
if __name__ == "__main__":
    app.run()