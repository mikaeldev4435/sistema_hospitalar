from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3

app = Flask(__name__)

app.secret_key = 'chave_super_secreta_projeto_hospital'

# Configuração inicial do banco de dados com as NOVAS tabelas
def init_db():
    conn = sqlite3.connect('gestao_hospitalar.db')
    cursor = conn.cursor()

    # 1. Tabela de Usuários (Base para Login e Segurança)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            tipo_perfil TEXT NOT NULL
        )
    ''')

    # 2. Tabela de Pacientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pacientes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nome TEXT NOT NULL,
            idade INTEGER,
            sexo TEXT,
            cpf TEXT UNIQUE,
            endereco TEXT,
            telefone TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')

    # 3. Tabela de Profissionais de Saúde
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profissionais(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nome TEXT NOT NULL,
            especialidade TEXT,
            registro_conselho TEXT UNIQUE,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')

    # 4. Tabela de Consultas (Com paciente_id e profissional_id)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consultas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            profissional_id INTEGER,
            data_hora TEXT,
            descricao TEXT,
            status TEXT DEFAULT 'Agendada',
            FOREIGN KEY(paciente_id) REFERENCES pacientes(id),
            FOREIGN KEY(profissional_id) REFERENCES profissionais(id)
        )
    ''')

    # 5. Tabela de Prontuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prontuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            profissional_id INTEGER,
            data_registro TEXT,
            diagnostico TEXT,
            observacoes TEXT,
            FOREIGN KEY(paciente_id) REFERENCES pacientes(id),
            FOREIGN KEY(profissional_id) REFERENCES profissionais(id)
        )
    ''')

    # 6. Tabela de Receitas (Prescrições)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS receitas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prontuario_id INTEGER,
            medicamento TEXT,
            dosagem TEXT,
            FOREIGN KEY(prontuario_id) REFERENCES prontuarios(id)
        )
    ''')

    # 7. Tabela de Leitos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leitos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE,
            status TEXT DEFAULT 'Livre',
            paciente_id INTEGER,
            FOREIGN KEY(paciente_id) REFERENCES pacientes(id)
        )
    ''')

    conn.commit()
    conn.close()


# Inicia o banco ao rodar o app
init_db()

# --- Porteiro do Sistema (Verifica se está logado) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# --- Rotas de Autenticação ---
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        tipo_perfil = request.form['tipo_perfil']  # Admin, Medico ou Paciente

        # Criptografa a senha antes de salvar no banco
        senha_hash = generate_password_hash(senha)

        conn = sqlite3.connect('gestao_hospitalar.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO usuarios (email, senha_hash, tipo_perfil) VALUES (?, ?, ?)',
                           (email, senha_hash, tipo_perfil))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Erro: Email já cadastrado!"
        finally:
            conn.close()

        return redirect(url_for('login'))

    return render_template('registro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        conn = sqlite3.connect('gestao_hospitalar.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, senha_hash, tipo_perfil FROM usuarios WHERE email = ?', (email,))
        usuario = cursor.fetchone()
        conn.close()

        # Verifica se o usuário existe e se a senha digitada bate com o hash criptografado
        if usuario and check_password_hash(usuario[1], senha):
            session['usuario_id'] = usuario[0]
            session['tipo_perfil'] = usuario[2]
            return redirect(url_for('index'))
        else:
            return "Email ou senha incorretos. Tente novamente."

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()  # Limpa a sessão
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    conn = sqlite3.connect('gestao_hospitalar.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pacientes')
    pacientes = cursor.fetchall()
    conn.close()
    return render_template('index.html', pacientes=pacientes)


@app.route('/novo_paciente', methods=['GET', 'POST'])
def novo_paciente():
    if request.method == 'POST':
        nome = request.form['nome']
        idade = request.form['idade']
        sexo = request.form['sexo']
        cpf = request.form['cpf']
        endereco = request.form['endereco']
        telefone = request.form['telefone']

        conn = sqlite3.connect('gestao_hospitalar.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pacientes (nome, idade, sexo, cpf, endereco, telefone)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nome, idade, sexo, cpf, endereco, telefone))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))
    return render_template('novo_paciente.html')


# NOVA ROTA: Cadastrar Profissional (Médico)
@app.route('/novo_profissional', methods=['GET', 'POST'])
def novo_profissional():
    if request.method == 'POST':
        nome = request.form['nome']
        especialidade = request.form['especialidade']
        registro_conselho = request.form['registro_conselho']

        conn = sqlite3.connect('gestao_hospitalar.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO profissionais (nome, especialidade, registro_conselho)
            VALUES (?, ?, ?)
        ''', (nome, especialidade, registro_conselho))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))
    return render_template('novo_profissional.html')


# ROTA ATUALIZADA: Agendar (Agora com escolha do Médico)
@app.route('/agendar/<int:paciente_id>', methods=['GET', 'POST'])
def agendar(paciente_id):
    conn = sqlite3.connect('gestao_hospitalar.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.form['data']
        hora = request.form['hora']
        descricao = request.form['descricao']
        profissional_id = request.form['profissional_id']  # Pega o médico escolhido

        data_hora = f"{data} {hora}"

        cursor.execute('''
            INSERT INTO consultas (paciente_id, profissional_id, data_hora, descricao)
            VALUES (?, ?, ?, ?)
            ''', (paciente_id, profissional_id, data_hora, descricao))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    # Quando abrir a tela (GET), busca a lista de médicos para o dropdown
    cursor.execute('SELECT id, nome, especialidade FROM profissionais')
    profissionais = cursor.fetchall()
    conn.close()

    return render_template('agendar.html', paciente_id=paciente_id, profissionais=profissionais)


@app.route('/consultas')
def listar_consultas():
    conn = sqlite3.connect('gestao_hospitalar.db')
    cursor = conn.cursor()

    # O comando JOIN conecta as 3 tabelas para trazer os nomes em vez dos IDs
    cursor.execute('''
        SELECT 
            consultas.id, 
            pacientes.nome, 
            profissionais.nome, 
            consultas.data_hora, 
            consultas.descricao, 
            consultas.status
        FROM consultas
        JOIN pacientes ON consultas.paciente_id = pacientes.id
        JOIN profissionais ON consultas.profissional_id = profissionais.id
        ORDER BY consultas.data_hora
    ''')
    consultas = cursor.fetchall()
    conn.close()

    return render_template('consultas.html', consultas=consultas)


@app.route('/prontuario/<int:paciente_id>', methods=['GET', 'POST'])
def prontuario(paciente_id):
    conn = sqlite3.connect('gestao_hospitalar.db')
    cursor = conn.cursor()

    # Se o formulário for enviado (POST), salva o novo registro no prontuário
    if request.method == 'POST':
        profissional_id = request.form['profissional_id']
        data_registro = request.form['data_registro']
        diagnostico = request.form['diagnostico']
        observacoes = request.form['observacoes']

        cursor.execute('''
            INSERT INTO prontuarios (paciente_id, profissional_id, data_registro, diagnostico, observacoes)
            VALUES (?, ?, ?, ?, ?)
        ''', (paciente_id, profissional_id, data_registro, diagnostico, observacoes))
        conn.commit()

        # Recarrega a página para mostrar o registro recém-adicionado
        return redirect(url_for('prontuario', paciente_id=paciente_id))

    # Se for GET (apenas abrir a página), busca os dados do paciente
    cursor.execute('SELECT * FROM pacientes WHERE id = ?', (paciente_id,))
    paciente = cursor.fetchone()

    # Busca o histórico do paciente cruzando com a tabela de profissionais (JOIN)
    cursor.execute('''
        SELECT prontuarios.id, prontuarios.data_registro, profissionais.nome, prontuarios.diagnostico, prontuarios.observacoes
        FROM prontuarios
        JOIN profissionais ON prontuarios.profissional_id = profissionais.id
        WHERE prontuarios.paciente_id = ?
        ORDER BY prontuarios.data_registro DESC
    ''', (paciente_id,))
    historico = cursor.fetchall()

    # Busca a lista de médicos para o formulário de novo registro
    cursor.execute('SELECT id, nome, especialidade FROM profissionais')
    profissionais = cursor.fetchall()

    conn.close()

    return render_template('prontuario.html', paciente=paciente, historico=historico, profissionais=profissionais)


@app.route('/receita/<int:prontuario_id>', methods=['GET', 'POST'])
def receita(prontuario_id):
    conn = sqlite3.connect('gestao_hospitalar.db')
    cursor = conn.cursor()

    # Se o médico preencheu o formulário, salva o medicamento
    if request.method == 'POST':
        medicamento = request.form['medicamento']
        dosagem = request.form['dosagem']

        cursor.execute('''
            INSERT INTO receitas (prontuario_id, medicamento, dosagem)
            VALUES (?, ?, ?)
        ''', (prontuario_id, medicamento, dosagem))
        conn.commit()
        return redirect(url_for('receita', prontuario_id=prontuario_id))

    # Busca os dados básicos do prontuário para mostrar no cabeçalho
    cursor.execute('''
        SELECT p.data_registro, p.diagnostico, pac.nome, prof.nome, pac.id
        FROM prontuarios p
        JOIN pacientes pac ON p.paciente_id = pac.id
        JOIN profissionais prof ON p.profissional_id = prof.id
        WHERE p.id = ?
    ''', (prontuario_id,))
    dados_prontuario = cursor.fetchone()

    # Busca os medicamentos já receitados neste prontuário
    cursor.execute('SELECT medicamento, dosagem FROM receitas WHERE prontuario_id = ?', (prontuario_id,))
    lista_receitas = cursor.fetchall()

    conn.close()

    return render_template('receita.html', prontuario_id=prontuario_id, dados=dados_prontuario, receitas=lista_receitas)


# --- Rota para Listar e Criar Leitos ---
@app.route('/leitos', methods=['GET', 'POST'])
def gerenciar_leitos():
    conn = sqlite3.connect('gestao_hospitalar.db')
    cursor = conn.cursor()

    # Se o formulário for enviado (POST), cria um novo leito
    if request.method == 'POST':
        numero = request.form['numero']
        try:
            cursor.execute('INSERT INTO leitos (numero) VALUES (?)', (numero,))
            conn.commit()
        except sqlite3.IntegrityError:
            # Ignora o erro se tentar cadastrar um número de leito que já existe
            pass
        return redirect(url_for('gerenciar_leitos'))

    # Busca os leitos e o nome do paciente (se houver alguém internado nele)
    cursor.execute('''
        SELECT leitos.id, leitos.numero, leitos.status, pacientes.nome
        FROM leitos
        LEFT JOIN pacientes ON leitos.paciente_id = pacientes.id
        ORDER BY leitos.numero
    ''')
    leitos = cursor.fetchall()

    # Busca a lista de pacientes para o dropdown de internação
    cursor.execute('SELECT id, nome FROM pacientes')
    pacientes = cursor.fetchall()

    conn.close()
    return render_template('leitos.html', leitos=leitos, pacientes=pacientes)


# --- Rota para Internar (Alocar) Paciente no Leito ---
@app.route('/alocar_leito/<int:leito_id>', methods=['POST'])
def alocar_leito(leito_id):
    paciente_id = request.form['paciente_id']

    conn = sqlite3.connect('gestao_hospitalar.db')
    cursor = conn.cursor()
    # Atualiza o leito para Ocupado e vincula o paciente
    cursor.execute('''
        UPDATE leitos
        SET status = 'Ocupado', paciente_id = ?
        WHERE id = ?
    ''', (paciente_id, leito_id))
    conn.commit()
    conn.close()

    return redirect(url_for('gerenciar_leitos'))


# --- Rota para Dar Alta (Liberar) o Leito ---
@app.route('/liberar_leito/<int:leito_id>')
def liberar_leito(leito_id):
    conn = sqlite3.connect('gestao_hospitalar.db')
    cursor = conn.cursor()
    # Remove o paciente e volta o status para Livre
    cursor.execute('''
        UPDATE leitos
        SET status = 'Livre', paciente_id = NULL
        WHERE id = ?
    ''', (leito_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('gerenciar_leitos'))

@app.route('/relatorios')
def relatorios():
    conn = sqlite3.connect('gestao_hospitalar.db')
    cursor = conn.cursor()

    # Conta o total de pacientes
    cursor.execute('SELECT COUNT(*) FROM pacientes')
    total_pacientes = cursor.fetchone()[0]

    # Conta o total de médicos/profissionais
    cursor.execute('SELECT COUNT(*) FROM profissionais')
    total_profissionais = cursor.fetchone()[0]

    # Conta o total de consultas agendadas/realizadas
    cursor.execute('SELECT COUNT(*) FROM consultas')
    total_consultas = cursor.fetchone()[0]

    # Conta o total de leitos cadastrados
    cursor.execute('SELECT COUNT(*) FROM leitos')
    total_leitos = cursor.fetchone()[0]

    # Conta apenas os leitos que estão com o status 'Ocupado'
    cursor.execute("SELECT COUNT(*) FROM leitos WHERE status = 'Ocupado'")
    leitos_ocupados = cursor.fetchone()[0]

    conn.close()

    # Calcula quantos leitos estão livres
    leitos_livres = total_leitos - leitos_ocupados

    return render_template('relatorios.html',
                           total_pacientes=total_pacientes,
                           total_profissionais=total_profissionais,
                           total_consultas=total_consultas,
                           total_leitos=total_leitos,
                           leitos_ocupados=leitos_ocupados,
                           leitos_livres=leitos_livres)



@app.route('/limpar_pacientes')
def limpar_pacientes():
    conn = sqlite3.connect('gestao_hospitalar.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM pacientes')
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)