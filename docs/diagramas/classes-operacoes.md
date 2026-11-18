# Diagrama de classes de projeto: documentação das operações

Complementa o diagrama de classes desta pasta, dividido em cinco páginas:

| Página | Arquivo | Conteúdo |
|---|---|---|
| 1 | `classes-1-visao-geral` | Classes e associações, sem atributos |
| 2 | `classes-2-vendas` | Atributos do pacote `vendas` |
| 3 | `classes-3-catalogo-estoque-contas` | Atributos de `catalogo`, `estoque` e `contas` |
| 4 | `classes-4-servicos-vendas` | Operações de `ServicosVendas` |
| 5 | `classes-5-servicos-estoque-catalogo-contas` | Operações dos demais serviços |

O estilo comum das páginas fica em `estilo.iuml`. Os tipos seguem a notação dos diagramas:
`Texto`, `Inteiro`, `Decimal`, `Booleano`, `Data`, `DataHora`. `[0..1]` indica valor
opcional e `[*]`, uma coleção.

A notação segue os slides "Diagrama de Classes" da disciplina:

- atributo: `[visibilidade] nome [multiplicidade] : tipo [= valor inicial] [{propriedades}]`;
- operação: `[visibilidade] nome (parâmetros) : tipo de retorno`;
- `/nome` indica atributo derivado; `{frozen}`, valor que não muda depois de criado;
- sublinhado indica operação ou atributo de classe.

As classes do Django que o sistema reaproveita (`AbstractUser`, `Group`) não aparecem nos
diagramas: os atributos herdados que o sistema usa estão na própria classe `Usuario`, e os
perfis aparecem como o atributo `perfis`.

Os serviços são módulos Python e aparecem nos diagramas como classes `<<serviço>>` cujas
operações são operações de classe (sublinhadas):

| Classe no diagrama | Módulo no código |
|---|---|
| `ServicosVendas` | `vendas/servicos.py` |
| `ServicosEstoque` | `estoque/servicos.py` |
| `ServicosCatalogo` | `catalogo/servicos.py` |
| `Perfis` | `contas/perfis.py` |
 Todas as operações que gravam dados rodam numa transação atômica: se uma
regra falhar, nada é gravado (RNF01). Uma regra violada lança `ValidationError`, que a
view mostra como mensagem na tela.

## ServicosVendas (`vendas/servicos.py`)

### Caixa

| Operação | Propósito | Parâmetros | Retorno |
|---|---|---|---|
| `obter_caixa_aberto()` | Localiza o caixa aberto no momento. | — | `Caixa [0..1]`: o caixa aberto, ou nada se estiver fechado. |
| `abrir_caixa(usuario, valor_inicial)` | Abrir Caixa. Impede abrir dois caixas ao mesmo tempo. | `usuario: Usuario` quem abre; `valor_inicial: Decimal` troco na gaveta, ≥ 0. | `Caixa` criado. Erro se o valor for negativo ou já houver caixa aberto. |
| `resumir_caixa(caixa)` | Totaliza o caixa para a conferência do fechamento. | `caixa: Caixa`. | `ResumoCaixa`: totais por forma de pagamento, estornos, total líquido, valor esperado em dinheiro e vendas em andamento. |
| `fechar_caixa(caixa, usuario, valor_contado, justificativa)` | Fechar Caixa: confere o dinheiro contado com o esperado. | `caixa: Caixa`; `usuario: Usuario` quem fecha; `valor_contado: Decimal` ≥ 0; `justificativa: Texto` (padrão vazio). | `Caixa` fechado. Erro se já estiver fechado, se houver venda em andamento ou se houver diferença sem justificativa. |

### Venda

| Operação | Propósito | Parâmetros | Retorno |
|---|---|---|---|
| `obter_venda_em_andamento(usuario, caixa)` | Recupera a venda que o operador deixou aberta no caixa atual. | `usuario: Usuario`; `caixa: Caixa [0..1]`. | `Venda [0..1]`. |
| `iniciar_ou_retomar_venda(usuario)` | Inicia uma venda ou retoma a que está em andamento. | `usuario: Usuario` operador. | `Venda` em andamento. Erro se o caixa estiver fechado. |
| `localizar_produtos_para_venda(termo)` | Identifica o produto pelo código interno, pelo código de barras ou por parte do nome. | `termo: Texto`. | `Produto [0..10]`: um produto, se o código bater; senão, até 10 produtos ativos pelo nome. |
| `adicionar_item(venda, produto, quantidade)` | Inclui um item na venda; produto repetido soma à quantidade. | `venda: Venda`; `produto: Produto` ativo; `quantidade: Inteiro` > 0 (padrão 1). | `ItemVenda`. Erro se a venda não estiver em andamento, o produto estiver inativo ou faltar saldo. |
| `alterar_quantidade(item, quantidade)` | Altera a quantidade de um item da venda. | `item: ItemVenda`; `quantidade: Inteiro` > 0. | `ItemVenda`. Erro se faltar saldo. |
| `remover_item(item)` | Retira um item da venda em andamento. | `item: ItemVenda`. | — |
| `cancelar_venda(venda)` | Cancelar Venda em Andamento, sem pagamento nem baixa de estoque. | `venda: Venda` em andamento. | `Venda` cancelada. |
| `verificar_finalizacao(venda)` | Confere a venda antes do pagamento. | `venda: Venda`. | — . Erro se a venda não tiver itens, tiver item inativo ou faltar saldo. |
| `calcular_troco(total, forma_pagamento, valor_recebido)` | Receber Pagamento: em dinheiro, exige quantia suficiente e calcula o troco. | `total: Decimal`; `forma_pagamento: FormaPagamento`; `valor_recebido: Decimal [0..1]`, obrigatório em dinheiro. | `(Decimal, Decimal)`: valor recebido e troco. Fora do dinheiro, o troco é zero. |
| `concluir_venda(venda, forma_pagamento, valor_recebido)` | Conclui a venda: registra o pagamento e baixa o estoque, tudo junto. | `venda: Venda`; `forma_pagamento: FormaPagamento`; `valor_recebido: Decimal [0..1]`. | `Venda` concluída. Erro se o caixa tiver sido fechado, faltar saldo ou a quantia for insuficiente. |
| `exigir_em_andamento(venda)` (privada) | Garante que a venda ainda pode ser alterada. | `venda: Venda`. | — . Erro se a venda não estiver em andamento. |
| `validar_quantidade(produto, quantidade)` (privada) | Valida a quantidade contra o saldo do produto. | `produto: Produto`; `quantidade: Inteiro`. | — . Erro se a quantidade for ≤ 0 ou maior que o saldo. |

### Devolução

| Operação | Propósito | Parâmetros | Retorno |
|---|---|---|---|
| `prazo_devolucao(venda)` | Calcula até quando a venda aceita devolução (7 dias após a conclusão). | `venda: Venda` concluída. | `DataHora`. |
| `motivo_devolucao_bloqueada(venda, agora)` | Diz se a venda aceita devolução agora e, se não aceitar, por quê. | `venda: Venda`; `agora: DataHora [0..1]` (padrão: o momento atual). | `Texto [0..1]`: nada se a devolução for permitida; senão, o motivo (venda não concluída, fora do prazo, tudo já devolvido ou caixa fechado). |
| `registrar_devolucao(venda, quantidades, motivo, usuario)` | Registrar Devolução: estorna pela mesma forma de pagamento e devolve os itens ao estoque. | `venda: Venda`; `quantidades: Mapa<id do ItemVenda, Inteiro>` a devolver de cada item; `motivo: Texto` obrigatório; `usuario: Usuario`. | `Devolucao`. Erro se a devolução estiver bloqueada, faltar motivo, nenhum item for informado, a quantidade passar do devolvível ou não houver dinheiro no caixa para o estorno. |

### Consulta e relatório

| Operação | Propósito | Parâmetros | Retorno |
|---|---|---|---|
| `filtrar_vendas(filtros)` | Consultar Vendas por número, situação, operador, caixa e período. | `filtros: FiltroVendas`, todos opcionais. | `Venda [*]`. |
| `gerar_relatorio_vendas(filtros)` | Gerar Relatórios Básicos: relatório das vendas concluídas da consulta. | `filtros: FiltroVendas` (a situação é sempre "concluída"). | `RelatorioVendas`: vendas, totais por forma de pagamento, total vendido, estornado e líquido. |

## ServicosEstoque (`estoque/servicos.py`)

| Operação | Propósito | Parâmetros | Retorno |
|---|---|---|---|
| `calcular_novo_saldo(tipo, saldo_atual, quantidade)` | Calcula o saldo resultante: a entrada soma; o ajuste substitui pelo saldo contado. | `tipo: TipoMovimentacao` (ENTRADA ou AJUSTE); `saldo_atual: Inteiro`; `quantidade: Inteiro`. | `Inteiro`. |
| `validar_movimentacao(tipo, produto, quantidade, motivo)` | Valida uma entrada ou um ajuste antes de registrar. | `tipo: TipoMovimentacao`; `produto: Produto`; `quantidade: Inteiro`; `motivo: MotivoAjuste [0..1]`. | — . Erro se o produto não controlar estoque, se for entrada em produto inativo, se a quantidade for inválida ou se faltar o motivo no ajuste. |
| `registrar_movimentacao(tipo, produto, quantidade, usuario, motivo, observacao)` | Realizar Transação no Estoque (entrada ou ajuste). | `tipo: TipoMovimentacao`; `produto: Produto`; `quantidade: Inteiro`; `usuario: Usuario`; `motivo: MotivoAjuste [0..1]`; `observacao: Texto` (padrão vazio). | `Movimentacao`, com o saldo do produto atualizado. |
| `registrar_baixa_por_venda(produto, quantidade, usuario, referencia)` | Baixa o estoque de um item na conclusão da venda. | `produto: Produto`; `quantidade: Inteiro`; `usuario: Usuario`; `referencia: Texto` (a venda). | `Movimentacao [0..1]`: nada se o produto não controlar estoque. Erro se faltar saldo. |
| `registrar_recomposicao_por_devolucao(produto, quantidade, usuario, referencia)` | Devolve ao saldo os itens de uma devolução. | `produto: Produto`; `quantidade: Inteiro` > 0; `usuario: Usuario`; `referencia: Texto` (a devolução). | `Movimentacao [0..1]`: nada se o produto não controlar estoque. |
| `gravar_movimentacao(...)` (privada) | Grava a movimentação e o novo saldo juntos. É o único ponto que altera `Produto.saldo_estoque`. | `produto: Produto` já bloqueado; `tipo: TipoMovimentacao`; `novo_saldo: Inteiro`; `usuario: Usuario`; `motivo: MotivoAjuste [0..1]`; `observacao: Texto`. | `Movimentacao`. |
| `filtrar_movimentacoes(filtros)` | Consultar Movimentação no Estoque por produto, tipo e período. | `filtros: FiltroMovimentacoes`. | `Movimentacao [*]`. |
| `gerar_relatorio_movimentacoes(filtros)` | Gerar Relatórios Básicos: relatório das movimentações da consulta. | `filtros: FiltroMovimentacoes`. | `RelatorioMovimentacoes`: registros do período e, por produto, entradas, ajustes, baixas, devoluções e saldo atual. |

## ServicosCatalogo (`catalogo/servicos.py`)

| Operação | Propósito | Parâmetros | Retorno |
|---|---|---|---|
| `pesquisar_produtos(termo, por, incluir_inativos, categoria)` | Consultar Produto por nome, código interno ou código de barras. | `termo: Texto` (padrão vazio); `por: PesquisarPor` (padrão NOME); `incluir_inativos: Booleano` (padrão falso); `categoria: Categoria [0..1]`. | `Produto [*]`. |
| `buscar_por_codigo(valor)` | Identifica um produto pelo código interno ou pelo código lido no leitor. | `valor: Texto`. | `Produto [0..1]`. |

## contas

| Operação | Propósito | Parâmetros | Retorno |
|---|---|---|---|
| `Perfis.possui_algum_perfil(usuario, perfis_permitidos)` | Verifica se o usuário pode usar uma tela. O superusuário sempre pode. | `usuario: Usuario`; `perfis_permitidos: Texto [1..3]`. | `Booleano`. |
| `PerfilRequeridoMixin.test_func()` | Aplicada em todas as telas: exige login e um dos perfis da tela. | — (usa o usuário da requisição e `perfis_permitidos`). | `Booleano`. Falso resulta em acesso negado (403). |

## Operações das entidades

| Classe | Operação | Retorno | Propósito |
|---|---|---|---|
| `Produto` | `/lucro_unitario` | `Decimal [0..1]` | Preço de venda menos preço de custo; nada sem custo. |
| `Produto` | `/margem_percentual` | `Decimal [0..1]` | Lucro sobre o preço de venda, em %. |
| `Caixa` | `/diferenca` | `Decimal [0..1]` | Valor contado menos valor esperado, depois do fechamento. |
| `Venda` | `/total_itens` | `Decimal` | Soma dos subtotais enquanto a venda está em andamento. |
| `Venda` | `/total_devolvido` | `Decimal` | Soma dos estornos das devoluções da venda. |
| `Venda` | `/total_liquido` | `Decimal` | Total da venda menos o devolvido. |
| `ItemVenda` | `/subtotal` | `Decimal` | Preço praticado × quantidade. |
| `ItemVenda` | `/quantidade_devolvida`, `/quantidade_devolvivel` | `Inteiro` | Quanto já voltou e quanto ainda pode voltar. |
| `ItemDevolucao` | `/subtotal` | `Decimal` | Valor estornado do item, pelo preço da venda. |
| `Usuario` | `/nomes_perfis` | `Texto [0..3]` | Perfis da conta, na ordem Diretoria, Bolsista, Voluntário. |
| `Produto`, `Movimentacao`, `Venda`, `Devolucao` | `get_absolute_url()` | `Texto` | Endereço da tela de detalhe do registro. |
