# Arquitetura do Sistema

O **Sistema de Controle de Vendas e Estoque da Lojinha do DACOMP** é um monólito **Django 5.2+** com banco de dados **PostgreSQL 17**, empacotado em containers Docker. A aplicação é organizada em pacotes (Django apps) por subsistema e estruturada internamente em camadas.

---

## 1. Visão Geral em Camadas e Dependências entre Pacotes

Cada subsistema segue o fluxo de responsabilidades `templates/` → `views.py` / `forms.py` → `servicos.py` → `models.py`.

```mermaid
flowchart TD
    Usuario(["Operador / Diretoria / Bolsista"]) --> Config["config (settings.py e urls.py)"]

    subgraph Apps["Subsistema / Pacotes Django"]
        Nucleo["nucleo (InicioView, templatetags, popular_demo)"]
        Vendas["vendas (Caixa, Venda, ItemVenda, PDV)"]
        Catalogo["catalogo (Produto, pesquisa, baixar_saldo)"]
        Contas["contas (Usuario, Perfis, PerfilRequeridoMixin, criar_conta)"]
    end

    Config --> Nucleo
    Config --> Vendas
    Config --> Catalogo
    Config --> Contas

    Nucleo --> Vendas
    Nucleo --> Catalogo
    Nucleo --> Contas

    Vendas --> Catalogo
    Vendas --> Contas
    Catalogo --> Contas

    subgraph Camadas["Padrão Interno por Pacote"]
        T["templates/ (Apresentação HTML)"] --> V["views.py e forms.py (Controle HTTP)"]
        V --> S["servicos.py (Regras de Negócio e Transações)"]
        S --> M["models.py (Entidades e Constraints)"]
    end

    Apps --> Camadas
    M --> DB[("PostgreSQL 17")]
```

### Responsabilidade de cada pacote

| Pacote     | Responsabilidade Principal                                                                                                                                               | Casos de Uso (UC01–UC17)           |
| :--------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------- |
| `config`   | Configurações globais (`settings.py`), WSGI/ASGI e roteamento raiz (`urls.py`).                                                                                          | —                                  |
| `contas`   | Autenticação (`LoginView`/`LogoutView`), modelo `Usuario`, perfis via `Group` (`Diretoria`, `Bolsista`, `Voluntário`), `PerfilRequeridoMixin` e comando `criar_conta`.   | UC01 (UC15 via CLI)                |
| `catalogo` | Cadastro, edição, ativação/inativação, pesquisa por nome/código/barras e baixa transacional de saldo (`baixar_saldo`).                                                   | UC02, UC13                         |
| `vendas`   | Abertura e fechamento de `Caixa`, operação do PDV, registro de `Venda`/`ItemVenda`, cálculo de troco, pagamento atômico, cancelamento em andamento e consulta de vendas. | UC03, UC04, UC05, UC06, UC07, UC17 |
| `nucleo`   | Dashboard inicial (`InicioView`), templatetags (`estaticos`, `formatacao`, `paginacao`) e comando `popular_demo`.                                                        | —                                  |

> [!NOTE]
> No modelo de análise (`Relatório Final - Lojinha DAcomp`), também estão previstos os pacotes/casos de uso de controle completo de estoque (`UC08`–`UC12`), relatórios básicos (`UC14`), gestão de contas pela interface web (`UC15`) e devolução/estorno (`UC16`). Na etapa atual do código, a gestão de contas é feita via CLI e as movimentações de estoque foram simplificadas para edição direta do saldo no produto.

---

## 2. Modelo de Dados (DER)

O diagrama abaixo representa as entidades persistidas no PostgreSQL e suas principais restrições de integridade:

- **`apenas_um_caixa_aberto`**: `UniqueConstraint` parcial garantindo que exista no máximo um `Caixa` com `situacao = "aberto"` por vez.
- **`produto_unico_por_venda`**: `UniqueConstraint` em `(venda, produto)` em `ItemVenda` (itens repetidos no PDV incrementam a `quantidade` do mesmo registro).

```mermaid
erDiagram
    USUARIO ||--o{ PRODUTO : "cria / altera"
    USUARIO ||--o{ CAIXA : "abre / fecha"
    USUARIO ||--o{ VENDA : "opera"
    CAIXA ||--o{ VENDA : "agrupa"
    VENDA ||--|{ ITEM_VENDA : "contem"
    PRODUTO ||--o{ ITEM_VENDA : "compoe"

    USUARIO {
        bigint id PK
        string username UK
        string first_name
        string last_name
        string email
        boolean is_active
        boolean is_superuser
    }

    PRODUTO {
        bigint id PK
        string codigo UK
        string nome
        string categoria
        string codigo_barras UK
        string unidade
        decimal preco_unitario
        decimal preco_custo
        boolean ativo
        boolean controla_estoque
        int saldo_estoque
        bigint criado_por_id FK
        bigint alterado_por_id FK
    }

    CAIXA {
        bigint id PK
        string situacao "aberto | fechado"
        decimal valor_inicial
        bigint aberto_por_id FK
        datetime aberto_em
        bigint fechado_por_id FK
        datetime fechado_em
        decimal valor_esperado
        decimal valor_contado
        string justificativa
    }

    VENDA {
        bigint id PK
        bigint caixa_id FK
        bigint operador_id FK
        string situacao "andamento | concluida | cancelada"
        datetime iniciada_em
        datetime concluida_em
        decimal total
        string forma_pagamento "dinheiro | pix | credito | debito"
        decimal valor_recebido
        decimal troco
    }

    ITEM_VENDA {
        bigint id PK
        bigint venda_id FK
        bigint produto_id FK
        int quantidade
        decimal preco_unitario "preco congelado na venda"
    }
```

---

## 3. Diagrama de Classes de Projeto

Em conformidade com os requisitos da **Etapa 3**, o diagrama abaixo apresenta as classes de domínio e seus serviços com **tipos, restrições, métodos/operações e navegabilidade definida**.

```mermaid
classDiagram
    direction TB

    class Usuario {
        +int id
        +str username
        +str first_name
        +str last_name
        +str email
        +bool is_active
        +bool is_superuser
        +nomes_perfis() list~str~
        +__str__() str
    }

    class Produto {
        +int id
        +str codigo
        +str nome
        +Categoria categoria
        +str codigo_barras
        +Unidade unidade
        +Decimal preco_unitario
        +Decimal preco_custo
        +bool ativo
        +bool controla_estoque
        +int saldo_estoque
        +lucro_unitario() Decimal
        +margem_percentual() Decimal
        +get_absolute_url() str
    }

    class Caixa {
        +int id
        +Situacao situacao
        +Decimal valor_inicial
        +datetime aberto_em
        +datetime fechado_em
        +Decimal valor_esperado
        +Decimal valor_contado
        +str justificativa
        +diferenca() Decimal
    }

    class Venda {
        +int id
        +Situacao situacao
        +datetime iniciada_em
        +datetime concluida_em
        +Decimal total
        +FormaPagamento forma_pagamento
        +Decimal valor_recebido
        +Decimal troco
        +total_itens() Decimal
        +get_absolute_url() str
    }

    class ItemVenda {
        +int id
        +int quantidade
        +Decimal preco_unitario
        +subtotal() Decimal
    }

    class ServicoCatalogo {
        +pesquisar_produtos(termo: str, por: PesquisarPor, incluir_inativos: bool, categoria: str) QuerySet~Produto~
        +buscar_por_codigo(valor: str) Produto
        +baixar_saldo(produto: Produto, quantidade: int) Produto
    }

    class ServicoVendas {
        +abrir_caixa(usuario: Usuario, valor_inicial: Decimal) Caixa
        +resumir_caixa(caixa: Caixa) dict
        +fechar_caixa(caixa: Caixa, usuario: Usuario, valor_contado: Decimal, justificativa: str) Caixa
        +iniciar_ou_retomar_venda(usuario: Usuario) Venda
        +adicionar_item(venda: Venda, produto: Produto, quantidade: int) ItemVenda
        +concluir_venda(venda: Venda, forma_pagamento: str, valor_recebido: Decimal) Venda
        +cancelar_venda(venda: Venda) Venda
    }

    Produto "*" --> "1" Usuario : criado_por / alterado_por
    Caixa "*" --> "1" Usuario : aberto_por / fechado_por
    Venda "*" --> "1" Caixa : caixa
    Venda "*" --> "1" Usuario : operador
    Venda "1" *-- "0..*" ItemVenda : itens
    ItemVenda "*" --> "1" Produto : produto
    ServicoCatalogo ..> Produto : consulta e atualiza saldo
    ServicoVendas ..> Caixa : gerencia
    ServicoVendas ..> Venda : gerencia
    ServicoVendas ..> ServicoCatalogo : chama baixar_saldo
```

### Documentação das Principais Operações

| Classe / Módulo     | Operação             | Propósito                                                                            | Parâmetros (Tipos)                                                                 | Valor de Retorno    |
| :------------------ | :------------------- | :----------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------- | :------------------ |
| `Produto`           | `lucro_unitario`     | Calcula o lucro por unidade vendida (`preco_unitario - preco_custo`).                | —                                                                                  | `Decimal \| None`   |
| `Produto`           | `margem_percentual`  | Calcula a margem de lucro percentual sobre o preço de venda.                         | —                                                                                  | `Decimal \| None`   |
| `Caixa`             | `diferenca`          | Calcula a diferença entre `valor_contado` e `valor_esperado`.                        | —                                                                                  | `Decimal \| None`   |
| `Venda`             | `total_itens`        | Soma os subtotais de todos os `ItemVenda` associados.                                | —                                                                                  | `Decimal`           |
| `ItemVenda`         | `subtotal`           | Calcula o valor do item (`preco_unitario * quantidade`).                             | —                                                                                  | `Decimal`           |
| `catalogo.servicos` | `pesquisar_produtos` | Filtra produtos por nome, código interno, código de barras, categoria e status.      | `termo: str`, `por: PesquisarPor`, `incluir_inativos: bool`, `categoria: str`      | `QuerySet[Produto]` |
| `catalogo.servicos` | `baixar_saldo`       | Reduz `saldo_estoque` com `select_for_update()` se `controla_estoque=True`.          | `produto: Produto`, `quantidade: int`                                              | `Produto`           |
| `vendas.servicos`   | `abrir_caixa`        | Abre um novo caixa se não houver outro aberto e `valor_inicial >= 0`.                | `usuario: Usuario`, `valor_inicial: Decimal`                                       | `Caixa`             |
| `vendas.servicos`   | `resumir_caixa`      | Consolida vendas concluídas por forma de pagamento e calcula `valor_esperado`.       | `caixa: Caixa`                                                                     | `dict`              |
| `vendas.servicos`   | `fechar_caixa`       | Fecha o caixa validando ausência de venda em andamento e justificativa de diferença. | `caixa: Caixa`, `usuario: Usuario`, `valor_contado: Decimal`, `justificativa: str` | `Caixa`             |
| `vendas.servicos`   | `concluir_venda`     | Grava pagamento, troco e baixa de estoque atomicamente (`@transaction.atomic`).      | `venda: Venda`, `forma_pagamento: str`, `valor_recebido: Decimal \| None`          | `Venda`             |

---

## 4. Controle de Acesso e Perfis

Os perfis são implementados como `Group` do Django em `contas/perfis.py`, permitindo que um usuário acumule mais de um papel. O acesso às views é protegido por `contas.mixins.PerfilRequeridoMixin`.

| Funcionalidade / View                                                                          | `Diretoria` | `Bolsista` | `Voluntário` |
| :--------------------------------------------------------------------------------------------- | :---------: | :--------: | :----------: |
| Tela inicial (`nucleo:inicio`)                                                                 |     ✅      |     ✅     |      ✅      |
| Consultar e detalhar produtos (`catalogo:lista_produtos`, `detalhe_produto`)                   |     ✅      |     ✅     |      ✅      |
| Cadastrar, editar e ativar/inativar produtos (`PERFIS_GESTAO_PRODUTOS`)                        |     ✅      |     ✅     |      ❌      |
| Abrir e fechar caixa (`vendas:abrir_caixa`, `fechar_caixa`)                                    |     ✅      |     ✅     |      ✅      |
| Operar PDV e concluir/cancelar vendas (`vendas:pdv`, `pagamento`, etc.)                        |     ✅      |     ✅     |      ✅      |
| Consultar e detalhar vendas e caixas (`vendas:lista_vendas`, `detalhe_venda`, `detalhe_caixa`) |     ✅      |     ✅     |      ✅      |
| Gestão de contas (`criar_conta`, `changepassword` via CLI)                                     |      —      |     —      |      —       |

---

## 5. Mapa de Rotas (URLs)

Todas as rotas da aplicação são centralizadas em `config/urls.py`:

| Prefixo      | App                    | Principais Endpoints                                                                                                                               |
| :----------- | :--------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/`          | `nucleo`               | `/` (`inicio`)                                                                                                                                     |
| `/conta/`    | `contas`               | `/conta/entrar/`, `/conta/sair/`                                                                                                                   |
| `/produtos/` | `catalogo`             | `/produtos/`, `/produtos/novo/`, `/produtos/<pk>/`, `/produtos/<pk>/editar/`, `/produtos/<pk>/situacao/`                                           |
| `/vendas/`   | `vendas`               | `/vendas/pdv/`, `/vendas/pdv/<pk>/pagamento/`, `/vendas/caixa/abrir/`, `/vendas/caixa/fechar/`, `/vendas/caixa/<pk>/`, `/vendas/`, `/vendas/<pk>/` |
| `/admin/`    | `django.contrib.admin` | Painel administrativo padrão do Django                                                                                                             |
