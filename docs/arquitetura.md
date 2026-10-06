# Arquitetura do sistema

O sistema da lojinha do DACOMP é um monólito Django organizado em camadas e dividido em pacotes por responsabilidade. A aplicação e o banco PostgreSQL rodam em serviços separados do Docker Compose.

Essa escolha atende ao tamanho do projeto e mantém a execução simples. A conclusão de uma venda envolve o pagamento e o estoque. Manter essas operações na mesma aplicação permite gravá-las em uma única transação de banco, evitando uma venda concluída sem o registro correspondente de pagamento ou de baixa.

## Pacotes

| Pacote | Responsabilidade | Dependências internas |
| --- | --- | --- |
| `contas` | Autenticação, contas internas, perfis fixos e controle de acesso | Não usa os outros pacotes do negócio |
| `catalogo` | Cadastro, pesquisa, detalhes e saldo dos produtos e serviços | `contas` |
| `estoque` | Entradas, ajustes, baixas de venda e histórico de movimentações | `catalogo`, `contas` |
| `vendas` | PDV, pagamento, abertura e fechamento de caixa e consultas de vendas | `catalogo`, `estoque`, `contas` |
| `nucleo` | Página inicial, formatação, paginação e dados de demonstração | `catalogo`, `estoque`, `vendas`, `contas` |
| `config` | Configurações, registro das rotas e composição da aplicação | Registra os cinco pacotes e define `contas.Usuario` como usuário do projeto |

O [diagrama de pacotes](https://lucid.app/lucidchart/92abb5cb-ec36-47da-bed2-f6d2120cda91/edit) mostra essas dependências. As setas tracejadas saem do pacote que usa uma responsabilidade e apontam para o pacote usado. O arquivo editável de diagramas acompanha a entrega da Etapa 2.

## Camadas dentro dos pacotes

Os arquivos `models.py` definem as entidades e seus vínculos no banco. Os arquivos `servicos.py` concentram as regras de negócio, como validar uma quantidade, concluir uma venda ou registrar uma movimentação. Os formulários validam as entradas, as views conduzem as ações e os templates apresentam o resultado no navegador.

Nas vendas, `vendas.servicos` consulta o catálogo e chama `estoque.servicos` para registrar a baixa dos produtos físicos. O estoque bloqueia a atualização concorrente do produto durante a transação, verifica o saldo e registra os valores anterior e posterior da movimentação. Serviços cadastrados sem controle de estoque permanecem nos itens da venda, sem baixa de quantidade.

As interfaces usam `contas` para identificar o operador e aplicar as permissões. Diretoria e Bolsistas mantêm o cadastro de produtos. Os três perfis fixos compartilham as operações de atendimento, caixa e estoque.

## Tecnologias

- Python é a linguagem do sistema.
- Django oferece rotas, autenticação, formulários, templates e acesso ao banco pelo ORM.
- PostgreSQL 17 armazena produtos, movimentações, vendas, pagamentos e caixas.
- HTML e CSS compõem a interface acessada pelo navegador.
- Docker Compose executa a aplicação e o banco no ambiente local.
- pytest e pytest-django verificam os serviços, os fluxos de atendimento e as permissões.

## Recorte da Etapa 2

Catálogo, estoque, vendas, pagamentos e caixa já têm implementação. O sistema registra dinheiro, PIX, crédito ou débito conforme a confirmação do operador, sem integração com bancos ou operadoras. A geração dos relatórios básicos, UC50, fica prevista para a Etapa 3. As consultas em tela já funcionam.
