# Arquitetura do sistema

O sistema da lojinha do DACOMP é um monólito Django organizado em camadas e dividido em pacotes por responsabilidade. A aplicação e o banco PostgreSQL rodam em serviços separados do Docker Compose.

Essa escolha atende ao tamanho do projeto e mantém a execução simples. A conclusão de uma venda envolve o pagamento e o estoque. Manter essas operações na mesma aplicação permite gravá-las em uma única transação de banco, evitando uma venda concluída sem o registro correspondente de pagamento ou de baixa.

## Pacotes

| Pacote | Responsabilidade | Dependências internas |
| --- | --- | --- |
| `contas` | Autenticação, perfis fixos, controle de acesso e preparação de contas pelo terminal | Não usa os outros pacotes do negócio |
| `catalogo` | Cadastro, pesquisa, detalhes e saldo dos produtos e serviços | `contas` |
| `vendas` | PDV, pagamento, abertura e fechamento de caixa e consultas de vendas | `catalogo`, `contas` |
| `nucleo` | Página inicial, formatação, paginação e dados de demonstração | `catalogo`, `vendas`, `contas` |
| `config` | Configurações, registro das rotas e composição da aplicação | Registra os quatro pacotes da aplicação e define `contas.Usuario` como usuário do projeto |

O [diagrama de pacotes](https://lucid.app/lucidchart/92abb5cb-ec36-47da-bed2-f6d2120cda91/edit) mostra essas dependências. As setas tracejadas saem do pacote que usa uma responsabilidade e apontam para o pacote usado. O arquivo editável de diagramas acompanha a entrega da Etapa 2.

## Camadas dentro dos pacotes

Nos pacotes de negócio, os arquivos `models.py` definem as entidades e seus vínculos no banco. Os arquivos `servicos.py` de catálogo e vendas concentram regras como consultar produtos, validar quantidades, baixar o saldo e concluir uma venda. Os formulários validam as entradas, as views conduzem as ações e os templates apresentam o resultado no navegador. `contas` reúne também os comandos de administração das contas; `nucleo` contém as utilidades compartilhadas.

Nas vendas, `vendas.servicos` consulta o catálogo e chama `catalogo.servicos.baixar_saldo`. Essa operação bloqueia a atualização concorrente do produto e verifica o saldo disponível. Venda, pagamento e redução das quantidades são gravados na mesma transação: se um item não tiver saldo, a conclusão inteira é desfeita. Serviços e itens preparados na hora cadastrados sem controle de estoque permanecem na venda, sem baixa de quantidade.

As interfaces usam `contas` para identificar o operador e aplicar as permissões. Diretoria e Bolsistas mantêm os produtos e informam o saldo no cadastro. Os três perfis fixos consultam produtos e vendas, atendem no PDV e operam o caixa. A preparação de contas, perfis e senhas ocorre pela linha de comando de quem administra a instalação. UC15 descreve a futura interface da Diretoria, prevista para a Etapa 3.

## Tecnologias

- Python é a linguagem do sistema.
- Django oferece rotas, autenticação, formulários, templates e acesso ao banco pelo ORM.
- PostgreSQL 17 armazena produtos, usuários, vendas, pagamentos e caixas.
- HTML e CSS compõem a interface acessada pelo navegador.
- Docker Compose executa a aplicação e o banco no ambiente local.
- pytest e pytest-django verificam os serviços, os fluxos de atendimento e as permissões.

## Recorte da Etapa 2

Autenticação, catálogo, consulta de saldo, vendas, pagamentos e caixa já têm implementação. O sistema registra dinheiro, PIX, crédito ou débito conforme a confirmação do operador, sem integração com bancos ou operadoras.

O grupo retirou o pacote `estoque` e a interface de contas para simplificar a Etapa 2. O saldo é editado diretamente no cadastro, sem histórico de movimentações, e reduzido automaticamente nas vendas concluídas. UC09 a UC12 continuam no modelo para a Etapa 3. UC08 é atendido pelas consultas do catálogo. UC14 prevê somente dois relatórios: Vendas e Posição de Estoque, a partir de UC07 e UC08. A interface de UC15 também fica para a Etapa 3.

UC16 Registrar Devolução está especificado como extensão opcional de UC07 Consultar Vendas e será implementado na Etapa 3. O modelo prevê o retorno de itens, o registro do estorno e a atualização conjunta do estoque e do caixa. Essas operações ainda não fazem parte do código. O cancelamento de uma venda em andamento, antes do recebimento, já está disponível.
