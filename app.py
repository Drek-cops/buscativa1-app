import csv
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import smtplib
from email.message import EmailMessage

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
MONITORES_FILE = os.path.join(BASE_DIR, 'monitores.csv')
CSV_FOLDER = os.path.join(BASE_DIR, 'data')
os.makedirs(CSV_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'troque-essa-chave-por-uma-segura')

# Helper: carregar monitores
def carregar_monitores():
    monitors = {}
    if not os.path.exists(MONITORES_FILE):
        return monitors
    with open(MONITORES_FILE, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        for row in reader:
            if not row:
                continue
            if row[0].strip().lower() == 'usuario':
                continue
            if len(row) < 4:
                continue
            usuario, senha, nome_completo, turno = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
            monitors[usuario] = {
                'senha': senha,
                'nome_completo': nome_completo,
                'turno': turno
            }
    return monitors

# Helper: nome do arquivo mensal em português
MONTHS_PT = ['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro']

def nome_arquivo_mensal(date_obj=None):
    if date_obj is None:
        date_obj = datetime.now()
    month_name = MONTHS_PT[date_obj.month - 1]
    return os.path.join(CSV_FOLDER, f'faltas_{month_name}_{date_obj.year}.csv')

# Helper: salvar falta
def salvar_falta(data_dict):
    filename = nome_arquivo_mensal()
    exists = os.path.exists(filename)
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(['timestamp', 'monitor_usuario', 'monitor_nome', 'monitor_turno', 'aluno_nome', 'data_falta', 'motivo'])
        writer.writerow([
            datetime.now().isoformat(),
            data_dict.get('monitor_usuario',''),
            data_dict.get('monitor_nome',''),
            data_dict.get('monitor_turno',''),
            data_dict.get('aluno_nome',''),
            data_dict.get('data_falta',''),
            data_dict.get('motivo','')
        ])
    return filename

# Helper: enviar email (anexa o arquivo mensal inteiro)
def enviar_email_notificacao(row_dict, attachment_path):
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    recipient = os.environ.get('RECIPIENT_EMAIL')

    if not (smtp_server and smtp_user and smtp_pass and recipient):
        app.logger.warning('Config SMTP incompleta — email não será enviado')
        return False

    msg = EmailMessage()
    msg['Subject'] = f"[BUSCATIVA] Falta registrada: {row_dict.get('aluno_nome','') }"
    msg['From'] = smtp_user
    msg['To'] = recipient

    body = (
        f"Monitor: {row_dict.get('monitor_nome','')} ({row_dict.get('monitor_usuario','')})\n"
        f"Turno: {row_dict.get('monitor_turno','')}\n"
        f"Aluno: {row_dict.get('aluno_nome','')}\n"
        f"Data da falta: {row_dict.get('data_falta','')}\n"
        f"Motivo: {row_dict.get('motivo','')}\n"
        f"Registrado em: {datetime.now().isoformat()}\n\n"
        "Arquivo mensal anexo."
    )
    msg.set_content(body)

    # Anexar arquivo mensal (se existir)
    try:
        with open(attachment_path, 'rb') as af:
            file_data = af.read()
            file_name = os.path.basename(attachment_path)
            msg.add_attachment(file_data, maintype='text', subtype='csv', filename=file_name)
    except Exception as e:
        app.logger.warning(f'Não foi possível anexar o arquivo: {e}')

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)
        app.logger.info('Email enviado com sucesso')
        return True
    except Exception as e:
        app.logger.error(f'Erro ao enviar email: {e}')
        return False

# Rotas
@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('registro'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario','').strip()
        senha = request.form.get('senha','').strip()
        monitors = carregar_monitores()
        if usuario in monitors and monitors[usuario]['senha'] == senha:
            session['usuario'] = usuario
            session['monitor_nome'] = monitors[usuario]['nome_completo']
            session['monitor_turno'] = monitors[usuario]['turno']
            flash('Login feito com sucesso', 'success')
            return redirect(url_for('registro'))
        else:
            flash('Usuário ou senha inválidos', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Desconectado', 'info')
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET','POST'])
def registro():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        aluno_nome = request.form.get('aluno_nome','').strip()
        data_falta = request.form.get('data_falta','').strip()
        motivo = request.form.get('motivo','').strip()
        row = {
            'monitor_usuario': session.get('usuario',''),
            'monitor_nome': session.get('monitor_nome',''),
            'monitor_turno': session.get('monitor_turno',''),
            'aluno_nome': aluno_nome,
            'data_falta': data_falta,
            'motivo': motivo
        }
        arquivo = salvar_falta(row)
        enviado = enviar_email_notificacao(row, arquivo)
        if enviado:
            flash('Falta registrada e email enviado', 'success')
        else:
            flash('Falta registrada, mas não foi possível enviar o email (ver logs)', 'warning')
        return redirect(url_for('registro'))

    return render_template('registro.html', monitor_nome=session.get('monitor_nome',''), monitor_turno=session.get('monitor_turno',''))

# Rota opcional para baixar o arquivo mensal (somente quem estiver logado)
@app.route('/baixar')
def baixar():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    arquivo = nome_arquivo_mensal()
    if os.path.exists(arquivo):
        return send_file(arquivo, as_attachment=True)
    flash('Arquivo mensal não encontrado', 'danger')
    return redirect(url_for('registro'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))