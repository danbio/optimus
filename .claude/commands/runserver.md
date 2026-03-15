Inicia o servidor de desenvolvimento Django acessível na rede local.

`python manage.py runserver 0.0.0.0:8000`

Use `0.0.0.0:8000` (não `127.0.0.1:8000`) para que a equipe consiga acessar pelo IP local do computador de desenvolvimento.

Antes de rodar, verifique se:
- O IP local da máquina (ex: `192.168.1.x`) está em `ALLOWED_HOSTS` no `.env` ou `settings.py`
- O venv está ativo (`.venv\Scripts\activate` no Windows)

A equipe acessa via `http://<IP-da-maquina>:8000`.