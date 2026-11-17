# Fluxos de Negócio e Máquinas de Estado

Este documento detalha os principais fluxos operacionais implementados na camada de serviços (`vendas/servicos.py` e `catalogo/servicos.py`).

---

## 1. Máquinas de Estado: Caixa e Venda

### Ciclo de Vida do `Caixa`

Apenas um caixa pode permanecer `aberto` por vez (garantido pela constraint `apenas_um_caixa_aberto` e verificado em `abrir_caixa`). O fechamento exige que não haja nenhuma venda `em andamento` naquele caixa.

```mermaid
stateDiagram-v2
    [*] --> Aberto: abrir_caixa (valor_inicial >= 0)
    Aberto --> Fechado: fechar_caixa (sem vendas em andamento e justificativa se diferenca != 0)
    Fechado --> [*]
```

### Ciclo de Vida da `Venda`

```mermaid
stateDiagram-v2
    [*] --> EmAndamento: iniciar_ou_retomar_venda (exige Caixa aberto)
    EmAndamento --> EmAndamento: adicionar_item / alterar_quantidade / remover_item
    EmAndamento --> Cancelada: cancelar_venda (nao altera estoque)
    EmAndamento --> Concluida: concluir_venda (transacao atomica + baixa de estoque)
    Cancelada --> [*]
    Concluida --> [*]
```

---

## 2. Fluxo de Venda no PDV e Pagamento Atômico (RNF01)

Ao concluir uma venda, o sistema executa `vendas.servicos.concluir_venda` dentro de `@transaction.atomic` com bloqueio pessimista (`select_for_update()`), garantindo que pagamento e baixa de estoque ocorram juntos ou sejam totalmente revertidos em caso de erro (como falta de saldo).

```mermaid
sequenceDiagram
    actor Op as Operador
    participant View as PdvView / PagamentoView
    participant VS as vendas.servicos
    participant CS as catalogo.servicos
    participant DB as PostgreSQL

    Op->>View: Acessa /vendas/pdv/
    View->>VS: iniciar_ou_retomar_venda(usuario)
    VS->>DB: Verifica caixa aberto e venda em andamento
    DB-->>View: Venda (Em andamento)

    Op->>View: Busca produto (codigo, barras ou nome) e adiciona item
    View->>VS: adicionar_item(venda, produto, quantidade)
    VS->>DB: Valida produto ativo e saldo suficiente
    DB-->>View: ItemVenda criado ou quantidade somada

    Op->>View: Finaliza venda (F4) e informa pagamento
    View->>VS: concluir_venda(venda, forma_pagamento, valor_recebido)
    Note over VS,DB: Inicio de @transaction.atomic
    VS->>DB: Venda.objects.select_for_update()
    VS->>VS: verificar_finalizacao(venda)
    VS->>VS: calcular_troco(total, forma_pagamento, valor_recebido)

    loop Para cada ItemVenda
        VS->>CS: baixar_saldo(produto, quantidade)
        CS->>DB: Produto.objects.select_for_update()
        alt Produto controla_estoque e quantidade > saldo_estoque
            CS-->>VS: ValidationError (desfaz transacao)
        else Saldo suficiente ou nao controla estoque
            CS->>DB: Atualiza saldo_estoque
        end
    end

    VS->>DB: Salva Venda (situacao=concluida, total, troco, concluida_em)
    Note over VS,DB: Fim de @transaction.atomic (commit)
    VS-->>View: Venda concluida
    View-->>Op: Exibe comprovante / resumo da venda
```

---

## 3. Fluxo de Abertura e Fechamento de Caixa

Na abertura, o operador informa o troco inicial em dinheiro (`valor_inicial`). No fechamento, `resumir_caixa` consolida as vendas concluídas por forma de pagamento e calcula o `valor_esperado` em dinheiro (`valor_inicial + recebido_em_dinheiro`). Se o `valor_contado` divergir do esperado, uma `justificativa` é obrigatória.

```mermaid
sequenceDiagram
    actor Op as Operador
    participant View as AbrirCaixaView / FecharCaixaView
    participant VS as vendas.servicos
    participant DB as PostgreSQL

    Op->>View: Abrir caixa com valor_inicial
    View->>VS: abrir_caixa(usuario, valor_inicial)
    VS->>DB: Verifica se ja existe Caixa aberto
    alt Ja existe caixa aberto
        VS-->>View: ValidationError
    else Nenhum caixa aberto
        VS->>DB: Cria Caixa (situacao=aberto)
        VS-->>View: Caixa aberto
    end

    Op->>View: Solicita fechamento do caixa
    View->>VS: resumir_caixa(caixa)
    VS->>DB: Agrega vendas concluidas por forma_pagamento
    DB-->>View: Totais por forma + valor_esperado

    Op->>View: Envia valor_contado e justificativa (se houver diferenca)
    View->>VS: fechar_caixa(caixa, usuario, valor_contado, justificativa)
    Note over VS,DB: @transaction.atomic + select_for_update()
    alt Existe venda em andamento ou diferenca sem justificativa
        VS-->>View: ValidationError
    else Tudo valido
        VS->>DB: Atualiza Caixa (situacao=fechado, fechado_por, fechado_em)
        VS-->>View: Caixa fechado
    end
```
