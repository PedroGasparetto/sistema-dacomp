# trab_eng_soft

Repositório para elaboração do trabalho da cadeira INF01127 - Engenharia de Software.

**Sistema de Controle de Vendas e Estoque da Lojinha do DACOMP**: aplicação web em Python + Django.

## Como executar

O sistema roda inteiro no Docker: um container com o banco **PostgreSQL 17** e outro com a aplicação
**Django**. Não é preciso instalar Python nem PostgreSQL na máquina, só o Docker.

### 1. Baixar e instalar o Docker

**Windows 10/11**

1. Baixe o **Docker Desktop for Windows** em https://www.docker.com/products/docker-desktop/.
2. Execute o instalador e mantenha marcada a opção **Use WSL 2 instead of Hyper-V**.
3. Reinicie o computador se o instalador pedir.
4. Se aparecer um aviso sobre o WSL, abra o PowerShell como administrador e rode `wsl --install`;
   depois reinicie.
5. Se o Docker reclamar de virtualização desativada, habilite *Intel VT-x* / *AMD-V* (SVM) na BIOS.

**macOS**

1. Baixe o **Docker Desktop for Mac** em https://www.docker.com/products/docker-desktop/, escolhendo
   *Apple Silicon* (M1/M2/M3/M4) ou *Intel* conforme o seu processador.
2. Abra o `.dmg` e arraste o Docker para a pasta **Aplicativos**.

**Linux (Ubuntu/Debian)**

Instale o Docker Engine com o plugin Compose seguindo https://docs.docker.com/engine/install/ e
adicione seu usuário ao grupo `docker` (`sudo usermod -aG docker $USER`, depois saia e entre na
sessão).

### 2. Abrir o Docker e conferir a instalação

No Windows e no macOS, abra o **Docker Desktop** e espere aparecer *Engine running* no canto
inferior. Ele precisa estar aberto sempre que for usar o sistema. Depois, em um terminal:

```bash
docker --version
docker compose version
```

Os dois comandos devem mostrar uma versão. Se aparecer *cannot connect to the Docker daemon*, o
Docker Desktop não está aberto.

### 3. Subir o sistema

Na pasta do projeto (depois de `git clone https://github.com/gbtaffarel/trab_eng_soft.git`):

```bash
docker compose up --build -d
```

Na primeira vez o Docker baixa as imagens e instala as dependências, o que leva alguns minutos.
As migrações do banco são aplicadas automaticamente. Em seguida, crie as contas e o cardápio de
demonstração:

```bash
docker compose exec web python manage.py popular_demo --senha <escolha-uma-senha>
```

Acesse http://localhost:8000 e entre com `diretoria`, `bolsista` ou `voluntario` e a senha escolhida.

### 4. Contas da equipe

A Diretoria cria, edita, inativa contas e redefine senhas em **Contas** (menu superior). Cada pessoa
troca a própria senha em **Alterar senha**, no menu do usuário.

A primeira conta da Diretoria de uma instalação nova é criada pela linha de comando:

```bash
# Criar conta (a senha é pedida no terminal); repita --perfil para acumular papéis
docker compose exec web python manage.py criar_conta ana --perfil diretoria --perfil bolsista --nome Ana

# Alterar os perfis, desativar ou reativar uma conta
docker compose exec web python manage.py criar_conta ana --perfil voluntario
docker compose exec web python manage.py criar_conta ana --desativar
docker compose exec web python manage.py criar_conta ana --reativar
```

Perfis: `diretoria`, `bolsista` e `voluntario`. Somente a Diretoria mantém as contas; Diretoria e
Bolsista mantêm o cadastro de produtos; os três perfis operam o PDV, o caixa, o estoque, as devoluções
e os relatórios.

### 5. Uso no dia a dia

| Para…                                   | Comando                                                         |
|-----------------------------------------|-----------------------------------------------------------------|
| Subir o sistema                         | `docker compose up -d`                                          |
| Ver se os containers estão rodando      | `docker compose ps`                                             |
| Acompanhar os logs da aplicação         | `docker compose logs -f web`                                    |
| Rodar os testes                         | `docker compose exec web pytest`                                |
| Criar migrações após mudar um modelo    | `docker compose exec web python manage.py makemigrations`       |
| Criar superusuário para o `/admin`      | `docker compose exec web python manage.py createsuperuser`      |
| Abrir o terminal do PostgreSQL          | `docker compose exec db psql -U lojinha -d lojinha`             |
| Parar o sistema (mantém os dados)       | `docker compose down`                                           |
| Apagar o banco e começar do zero        | `docker compose down -v`                                        |
| Reconstruir após mudar `requirements.txt` | `docker compose up --build -d`                                |

O código da pasta é montado dentro do container: ao salvar um arquivo, o servidor recarrega sozinho,
sem precisar reconstruir. Os dados do banco ficam no volume `sistema-dacomp_dados_postgres` e
continuam lá entre um `down` e outro `up`.

### Instalação na rede local do DA

O `docker-compose.yml` acima é para desenvolvimento (só abre no próprio computador). Para usar o
sistema nos computadores do DAcomp, siga [docs/instalacao-rede-local.md](docs/instalacao-rede-local.md):
um computador roda o sistema com `docker-compose.rede-local.yml` e os outros acessam pelo navegador.
O sistema não depende de internet: CSS e fontes ficam em `static/vendor`.

### Problemas comuns

- **Porta 8000 ou 5432 em uso:** feche o programa que usa a porta (outro servidor Django ou um
  PostgreSQL instalado na máquina) e rode `docker compose up -d` de novo.
- **Página não abre logo após subir:** a aplicação espera o banco ficar pronto; aguarde alguns
  segundos e confira com `docker compose logs web`.
- **Credenciais do banco:** o padrão `lojinha`/`lojinha` serve só para desenvolvimento. Para trocar,
  copie `.env.example` para `.env`, ajuste os valores e rode `docker compose down -v` e
  `docker compose up -d` (o banco é recriado com as novas credenciais).

## Arquitetura

Monólito Django em camadas, dividido em pacotes por subsistema. Cada pacote segue
`models.py` (entidades) → `servicos.py` (regras de negócio) → `forms.py`/`views.py` (controle) → `templates/` (apresentação).

| Pacote     | Responsabilidade                                                          | Casos de uso |
|------------|---------------------------------------------------------------------------|--------------|
| `contas`   | Autenticação, perfis fixos (Diretoria, Bolsista, Voluntário) e gestão de contas | Autenticar Usuário, Manter Contas |
| `catalogo` | Cadastro e pesquisa de produtos (categoria, unidade, custo e lucro)        | Consultar Produto, Manter Cadastro de Produtos |
| `estoque`  | Entradas, ajustes, saldo, histórico de movimentações e relatório de estoque | Realizar Transação no Estoque (entrada e ajuste), Consultar Saldo e Movimentações, Gerar Relatórios Básicos |
| `vendas`   | PDV, caixa, pagamento, cancelamento, devolução, consulta e relatório de vendas | Abrir e Fechar Caixa, Registrar Venda, Receber Pagamento, Cancelar Venda em Andamento, Registrar Devolução, Consultar Vendas, Gerar Relatórios Básicos |
| `nucleo`   | Página inicial, formatação, paginação e dados de demonstração              | — |
| `config`   | Configurações e rotas do projeto                                          | — |

Dependências: `vendas → estoque → catalogo → contas`; `nucleo` usa todos. O saldo de um produto só é
alterado pelo `estoque.servicos` (entradas, ajustes, baixas de venda e recomposições de devolução),
sempre junto com o registro da movimentação. Venda, pagamento e baixa de estoque são gravados em uma
única transação (RNF01), assim como devolução, estorno e recomposição do estoque. As listagens usam 10
registros por página.

### PDV

O catálogo é principalmente de bar e café (cafés, bebidas, lanches, salgados e doces), organizado
por categoria. Itens preparados na hora, como café coado, podem ser cadastrados sem controle de estoque.

Em **PDV**: abra o caixa e toque nos produtos da grade de atalhos (filtrada por categoria) ou leia o
código de barras (ou digite o código ou parte do nome) e pressione Enter. A comanda fica à direita,
com o total. Logo abaixo do total, escolha a forma de pagamento (dinheiro, PIX, crédito ou débito) e, em
dinheiro, informe a quantia recebida: o troco aparece na hora. `F4` (ou **Confirmar pagamento**)
conclui a venda sem sair do PDV, que fica pronto para a próxima, com o link da última venda. `F2` volta
ao campo de produto. O fechamento do caixa confere as vendas por forma de pagamento e exige
justificativa quando o valor contado difere do esperado.

### Turno de atendimento

O login vale por um turno: depois de `DURACAO_TURNO_MINUTOS` (padrão: 100 minutos, ajustável no
`.env`) a sessão termina e quem assume o caixa entra com a própria conta. A sessão também termina ao
fechar o navegador. O horário de fim aparece no menu do usuário ("Turno até…").

### Estoque

Em **Estoque → Nova transação**, registre uma entrada de reposição (soma ao saldo) ou um ajuste após
contagem (substitui o saldo e exige motivo). O sistema mostra o saldo anterior, a variação e o
resultado antes de confirmar. Produtos novos começam com saldo zero: dê entrada no estoque depois de
cadastrá-los.

### Devolução

Na tela de uma venda concluída, **Registrar devolução** permite devolver itens em até 7 dias
(`PRAZO_DEVOLUCAO_DIAS` em `config/settings.py`), com o caixa aberto. Informe a quantidade de cada item
e o motivo, confira o resumo e confirme: o valor é estornado pela mesma forma de pagamento da venda,
pelo preço praticado nela, e os produtos voltam ao estoque. Uma venda aceita devoluções parciais até
todos os itens serem devolvidos. Estornos em dinheiro saem do valor esperado no fechamento do caixa.

### Relatórios

Nas consultas de **Vendas** e de **Estoque**, **Gerar relatório** monta um relatório com os mesmos
filtros da consulta, pronto para imprimir:

- **Vendas:** vendas concluídas, totais por forma de pagamento, estornos de devoluções e total líquido.
- **Movimentações de estoque:** registros do período e, por produto, entradas, ajustes, baixas por
  venda, devoluções e saldo atual.
