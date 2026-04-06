from flask import Flask, render_template, request, redirect, session, jsonify 
import sqlite3 
from datetime import datetime

from agendamento import agendamento_bp
from chat import chat_bp

from pagamento import pagamento_bp

# ==================== CONFIGURAÇÃO INICIAL ====================
app = Flask(__name__)
app.secret_key = 'segredo123'

# Registro dos Blueprints
app.register_blueprint(agendamento_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(pagamento_bp)


# ==================== FUNÇÕES DO BANCO DE DADOS ====================

def conectar():
    """Conecta ao banco de dados SQLite"""
    return sqlite3.connect('banco.db')


def criar_banco():
    """Cria as tabelas do banco de dados se não existirem"""
    conn = conectar()
    cursor = conn.cursor()

    # Tabela de usuários
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        cpf TEXT,
        telefone TEXT,
        genero TEXT,
        nascimento TEXT,
        email TEXT UNIQUE,
        senha TEXT,
        tipo TEXT,
        plano TEXT,
        status_pagamento TEXT,
        data_criacao TEXT
    )
    ''')

    # Tabela de pagamentos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pagamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        plano TEXT,
        valor REAL,
        payment_id TEXT,
        status TEXT,
        data TEXT
    )
    ''')

    # Tabela de mensagens
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mensagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        mensagem TEXT,
        remetente TEXT,
        data TEXT
    )
    ''')

    # Contas padrão do sistema (admin)
    contas = [
        ("Médico", "", "", "", "", "contamedico@gmail.com", "qwe123", "medico"),
        ("Financeiro", "", "", "", "", "contafinanceiro@gmail.com", "qwe123", "financeiro"),
        ("Suporte", "", "", "", "", "contasuporte@gmail.com", "qwe123", "suporte"),
    ]

    for conta in contas:
        try:
            cursor.execute('''
            INSERT INTO usuarios (nome, cpf, telefone, genero, nascimento, email, senha, tipo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', conta)
        except:
            pass

    conn.commit()
    conn.close()

# Executar criação do banco
criar_banco()


# ==================== ROTAS DE AUTENTICAÇÃO ====================
# Gerencia login, cadastro e logout de usuários

@app.route('/')
def home():
    """Página inicial - formulário de login"""
    return render_template('login.html')


@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    """Cadastra um novo usuário do tipo cliente"""
    dados = request.form

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute('''
        INSERT INTO usuarios (nome, cpf, telefone, genero, nascimento, email, senha, tipo, data_criacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dados['nome'],
            dados['cpf'],
            dados['telefone'],
            dados['genero'],
            dados['nascimento'],
            dados['email'],
            dados['senha'],
            'cliente',
            datetime.now().strftime("%d/%m/%Y")
        ))

        conn.commit()
    except:
        conn.close()
        return "Usuário já existe!"

    conn.close()
    return redirect('/')


@app.route('/login', methods=['POST'])
def login():
    """Realiza login e redireciona conforme tipo de usuário"""
    email = request.form['email']
    senha = request.form['senha']

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT tipo FROM usuarios WHERE email=? AND senha=?
    ''', (email, senha))

    user = cursor.fetchone()
    conn.close()

    if user:
        tipo = user[0]
        session['usuario'] = email
        session['tipo'] = tipo

        if tipo == 'medico':
            return redirect('/medico')
        elif tipo == 'financeiro':
            return redirect('/financeiro')
        elif tipo == 'suporte':
            return redirect('/suporte')
        else:
            return redirect('/painel_cliente')

    return "Login inválido!"


@app.route('/logout')
def logout():
    """Remove os dados da sessão e faz logout"""
    session.clear()
    return redirect('/')


# ==================== ROTAS DE PÁGINAS POR TIPO DE USUÁRIO ====================
# Direciona cada tipo de usuário para sua área específica

@app.route('/painel_cliente')
def painel_cliente():
    """Painel do cliente (usuário comum)"""
    if 'tipo' not in session or session['tipo'] != 'cliente':
        return redirect('/')
    return render_template('painel_cliente.html')


@app.route('/medico')
def medico():
    """Painel do médico"""
    if 'tipo' not in session or session['tipo'] != 'medico':
        return redirect('/')
    return render_template('medico.html')


@app.route('/financeiro')
def financeiro():
    """Painel do financeiro"""
    if 'tipo' not in session or session['tipo'] != 'financeiro':
        return redirect('/')
    return render_template('financeiro.html')


@app.route('/suporte')
def suporte():
    """Dashboard do suporte com estatísticas e listagem"""
    if 'tipo' not in session or session['tipo'] != 'suporte':
        return redirect('/')

    conn = conectar()
    cursor = conn.cursor()

    # Total de clientes
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE tipo='cliente'")
    total_usuarios = cursor.fetchone()[0]

    hoje = datetime.now().strftime("%d/%m/%Y")

    # Consultas de hoje
    try:
        cursor.execute("SELECT COUNT(*) FROM consultas WHERE data = ?", (hoje,))
        consultas_hoje = cursor.fetchone()[0]
    except:
        consultas_hoje = 0

    # Total de mensagens
    try:
        cursor.execute("SELECT COUNT(*) FROM mensagens")
        total_mensagens = cursor.fetchone()[0]
    except:
        total_mensagens = 0

    # Lista de clientes
    cursor.execute("""
    SELECT id, nome, email, telefone, cpf, plano, genero, nascimento, status_pagamento, data_criacao
    FROM usuarios
    WHERE tipo='cliente'
    """)
    usuarios = cursor.fetchall()

    # Lista de consultas
    try:
        cursor.execute("""
        SELECT u.nome, c.medico, c.especialidade, c.data, c.status
        FROM consultas c
        JOIN usuarios u ON c.usuario_id = u.id
        ORDER BY c.data DESC
        """)
        consultas = cursor.fetchall()
    except:
        consultas = []

    conn.close()

    return render_template(
        'suporte.html',
        total_usuarios=total_usuarios,
        consultas_hoje=consultas_hoje,
        total_mensagens=total_mensagens,
        usuarios=usuarios,
        consultas=consultas
    )


# ==================== ROTAS DE PÁGINAS PÚBLICAS ====================
# Páginas acessíveis por qualquer usuário logado

@app.route('/agendamentos')
def agendamentos():
    """Página de agendamentos do cliente"""
    if 'usuario' not in session:
        return redirect('/')
    return render_template('agendamentos.html')


@app.route('/planos')
def planos():
    """Página de planos de assinatura"""
    if 'usuario' not in session:
        return redirect('/')
    return render_template('planos.html')


@app.route('/trabalhe_conosco')
def trabalhe():
    """Página de trabalho conosco"""
    return render_template('trabalhe_conosco.html')


@app.route('/contato')
def contato():
    """Página de contato / suporte"""
    return render_template('contato.html')


# ==================== ROTAS DE GERENCIAMENTO DE USUÁRIOS (SUPORTE) ====================
# CRUD de usuários - apenas para usuários do tipo suporte

@app.route('/criar_usuario', methods=['GET', 'POST'])
def criar_usuario():
    """Cria um novo usuário (cliente, médico, financeiro ou suporte)"""
    if 'tipo' not in session or session['tipo'] != 'suporte':
        return redirect('/')
    
    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        telefone = request.form['telefone']
        genero = request.form['genero']
        nascimento = request.form['nascimento']
        email = request.form['email']
        senha = request.form['senha']
        tipo = request.form['tipo']
        
        conn = conectar()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO usuarios (nome, cpf, telefone, genero, nascimento, email, senha, tipo, data_criacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nome, cpf, telefone, genero, nascimento, email, senha, tipo, datetime.now().strftime("%d/%m/%Y")))
            
            conn.commit()
            conn.close()
            return redirect('/suporte?msg=Usuário criado com sucesso!')
        except:
            conn.close()
            return redirect('/criar_usuario?erro=Email já existe!')
    
    return render_template('criar_usuario.html')


@app.route('/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
def editar_usuario(user_id):
    """Edita os dados de um usuário existente"""
    if 'tipo' not in session or session['tipo'] != 'suporte':
        return redirect('/')
    
    conn = conectar()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        telefone = request.form['telefone']
        genero = request.form['genero']
        nascimento = request.form['nascimento']
        email = request.form['email']
        tipo = request.form['tipo']
        
        cursor.execute('''
        UPDATE usuarios 
        SET nome=?, cpf=?, telefone=?, genero=?, nascimento=?, email=?, tipo=?
        WHERE id=?
        ''', (nome, cpf, telefone, genero, nascimento, email, tipo, user_id))
        
        conn.commit()
        conn.close()
        return redirect('/suporte?msg=Usuário atualizado com sucesso!')
    
    cursor.execute("SELECT id, nome, cpf, telefone, genero, nascimento, email, tipo FROM usuarios WHERE id=?", (user_id,))
    usuario = cursor.fetchone()
    conn.close()
    
    return render_template('editar_usuario.html', usuario=usuario)


@app.route('/deletar_usuario/<int:user_id>')
def deletar_usuario(user_id):
    """Remove um usuário do sistema"""
    if 'tipo' not in session or session['tipo'] != 'suporte':
        return redirect('/')
    
    conn = conectar()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM usuarios WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    
    return redirect('/suporte?msg=Usuário deletado com sucesso!')


@app.route('/usuario_senha/<int:user_id>')
def usuario_senha(user_id):
    """Retorna a senha do usuário (apenas para suporte)"""
    if 'tipo' not in session or session['tipo'] != 'suporte':
        return jsonify({"senha": ""})
    
    conn = conectar()
    cursor = conn.cursor()
    
    cursor.execute("SELECT senha FROM usuarios WHERE id=?", (user_id,))
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado:
        return jsonify({"senha": resultado[0]})
    return jsonify({"senha": ""})


# ==================== ROTAS DE BUSCA E PERFIL ====================

@app.route('/buscar_usuario')
def buscar_usuario():
    """Busca usuário por nome, email ou CPF e redireciona para o perfil"""
    termo = request.args.get('q')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id FROM usuarios
    WHERE nome LIKE ? OR email LIKE ? OR cpf LIKE ?
    LIMIT 1
    """, (f"%{termo}%", f"%{termo}%", f"%{termo}%"))

    user = cursor.fetchone()
    conn.close()

    if user:
        return redirect(f"/perfil/{user[0]}")
    else:
        return redirect('/suporte')


@app.route('/perfil/<int:user_id>')
def perfil(user_id):
    """Exibe o perfil completo de um usuário com suas consultas"""
    if 'tipo' not in session or session['tipo'] != 'suporte':
        return redirect('/')

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT nome, email, telefone, cpf, genero, nascimento, plano, status_pagamento, data_criacao
    FROM usuarios WHERE id=?
    """, (user_id,))
    usuario = cursor.fetchone()

    try:
        cursor.execute("""
        SELECT medico, especialidade, data, status
        FROM consultas
        WHERE usuario_id=?
        ORDER BY data DESC
        """, (user_id,))
        consultas = cursor.fetchall()
    except:
        consultas = []

    conn.close()

    return render_template("perfil.html", usuario=usuario, consultas=consultas)


# ==================== INICIALIZAÇÃO DO SERVIDOR ====================

if __name__ == "__main__":
    app.run(debug=True)