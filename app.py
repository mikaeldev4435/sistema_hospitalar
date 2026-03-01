from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)


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


@app.route('/')
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
        SELECT prontuarios.data_registro, profissionais.nome, prontuarios.diagnostico, prontuarios.observacoes
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