# Instalação na rede local do DAcomp

Na reunião de 17/11 ficou decidido que o sistema roda na rede interna e nos computadores do
próprio DAcomp, sem usar os servidores do INF. Um computador faz o papel de **servidor** (roda o
sistema e guarda o banco de dados) e os outros computadores da lojinha só abrem o navegador.

O sistema não precisa de internet para funcionar: CSS, fontes e imagens estão no próprio projeto.
A internet só é necessária durante a instalação, para baixar o Docker e as imagens.

## 1. Escolher o computador servidor

- Um computador que fique ligado durante o atendimento. Windows 10/11, macOS ou Linux.
- Instale o Docker como no README (seção "Baixar e instalar o Docker") e deixe-o abrir junto com o
  sistema operacional (Docker Desktop → Settings → General → "Start Docker Desktop when you sign in").
- Peça ao responsável pela rede um **IP fixo** para esse computador (ou uma reserva de IP no
  roteador). Se o IP mudar, os outros computadores deixam de encontrar o sistema.

Para descobrir o IP atual:

- Windows: `ipconfig` no PowerShell (linha "Endereço IPv4").
- macOS: Ajustes do Sistema → Rede → detalhes da conexão.
- Linux: `hostname -I`.

Nos exemplos abaixo, o IP é `192.168.0.10`.

## 2. Baixar o projeto e criar o `.env`

```bash
git clone https://github.com/PedroGasparetto/sistema-dacomp.git
cd sistema-dacomp
cp .env.example .env        # no PowerShell: copy .env.example .env
```

Edite o `.env`:

| Variável | O que colocar |
|---|---|
| `POSTGRES_PASSWORD` | Uma senha forte para o banco de dados. |
| `DJANGO_SECRET_KEY` | Uma chave longa e aleatória. Para gerar: `docker run --rm python:3.13-slim python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,192.168.0.10` (troque pelo IP do servidor; pode incluir o nome do computador). |
| `PORTA` | Porta aberta na rede. O padrão é `8000`. |
| `DURACAO_TURNO_MINUTOS` | Duração do turno em minutos. Ao fim dele, é preciso entrar de novo. O padrão é `100`. |

Guarde o `.env` com cuidado: ele tem as senhas e não vai para o GitHub.

## 3. Subir o sistema

```bash
docker compose -f docker-compose.rede-local.yml up -d --build
```

Na primeira vez o Docker baixa as imagens e monta a aplicação (alguns minutos). Depois disso o
sistema volta a subir sozinho quando o Docker abre (`restart: unless-stopped`).

Confira se está rodando:

```bash
docker compose -f docker-compose.rede-local.yml ps
docker compose -f docker-compose.rede-local.yml logs -f web
```

## 4. Criar a primeira conta da Diretoria

```bash
docker compose -f docker-compose.rede-local.yml exec web python manage.py criar_conta jorge --perfil diretoria --nome Jorge
```

A senha é pedida no terminal. As demais contas são criadas pela tela **Contas**, entrando com essa
conta da Diretoria.

## 5. Acessar dos computadores da lojinha

Em qualquer computador da mesma rede, abra o navegador em:

```
http://192.168.0.10:8000
```

Dica: crie um atalho na área de trabalho ou deixe essa página como inicial do navegador.

Se não abrir:

- **Firewall do servidor:** libere a porta 8000 para a rede privada. No Windows, o Docker Desktop
  costuma pedir essa permissão na primeira vez; aceite para "Redes privadas".
- **Erro 400 (Bad Request):** o endereço usado não está em `DJANGO_ALLOWED_HOSTS`. Acrescente o IP ou
  o nome e rode o comando do passo 3 de novo.
- **Outra rede:** o computador precisa estar na mesma rede (mesmo Wi-Fi ou cabo) que o servidor.

## 6. Cópia de segurança do banco

Os dados ficam no volume `lojinha-dacomp_dados_postgres` do computador servidor. Faça uma cópia
periodicamente (por exemplo, no fechamento da semana) e guarde em outro lugar (pen drive ou nuvem
do DA):

```bash
docker compose -f docker-compose.rede-local.yml exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup-lojinha.sql
```

Para restaurar uma cópia num banco novo:

```bash
docker compose -f docker-compose.rede-local.yml exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"' < backup-lojinha.sql
```

## 7. Atualizar para uma versão nova

```bash
git pull
docker compose -f docker-compose.rede-local.yml up -d --build
```

As migrações do banco rodam sozinhas ao subir. Faça uma cópia de segurança antes de atualizar.

## Parar o sistema

```bash
docker compose -f docker-compose.rede-local.yml down      # para, mantendo os dados
```

Não use `down -v` no servidor: o `-v` apaga o banco de dados.
