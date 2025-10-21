# Buscativa App

App simples em Flask para que monitores registrem faltas.

## Como usar (pelo celular)
1. Crie um repositório no GitHub (por exemplo: buscativa-app).
2. No app do GitHub ou navegador, crie/edite arquivos e cole o conteúdo deste projeto.
3. Suba o repositório e conecte ao Render.com.
4. No Render, adicione as variáveis de ambiente:
   - SECRET_KEY (recomendado)
   - SMTP_SERVER (ex: smtp.gmail.com)
   - SMTP_PORT (ex: 587)
   - SMTP_USER (seu email SMTP)
   - SMTP_PASS (senha ou app password)
   - RECIPIENT_EMAIL (email que receberá notificações)
5. Deploy no Render: Build `pip install -r requirements.txt`, Start `gunicorn app:app`.