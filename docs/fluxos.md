# Fluxos de Negócio e Máquinas de Estado

Este documento detalha os principais fluxos operacionais implementados na camada de serviços (`vendas/servicos.py` e `catalogo/servicos.py`).

---

## 1. Máquinas de Estado: Caixa e Venda

- **Caixa:** apenas um caixa pode permanecer `aberto` por vez (restrição `apenas_um_caixa_aberto`, validada em `abrir_caixa`). O fechamento exige que não haja nenhuma venda `em andamento` naquele caixa.
- **Venda:** enquanto está `em andamento`, permite incluir, alterar quantidade ou remover itens; ao concluir, baixa o estoque atomicamente; ao cancelar, não altera o estoque.

![Máquinas de Estado: Caixa e Venda](diagramas/diagrama_estados.drawio.svg)

*(Arquivo fonte editável: [diagrama_estados.drawio](diagramas/diagrama_estados.drawio))*

---

## 2. Fluxo de Venda no PDV e Pagamento Atômico (RNF01)

Ao concluir uma venda, o sistema executa `vendas.servicos.concluir_venda` dentro de `@transaction.atomic` com bloqueio pessimista (`select_for_update()`), garantindo que pagamento e baixa de estoque ocorram juntos ou sejam totalmente revertidos em caso de erro (como falta de saldo).

![Diagrama de Sequência: Venda no PDV e Pagamento](diagramas/sequencia_venda_pdv.drawio.svg)

*(Arquivo fonte editável: [sequencia_venda_pdv.drawio](diagramas/sequencia_venda_pdv.drawio))*

---

## 3. Fluxo de Abertura e Fechamento de Caixa

Na abertura, o operador informa o troco inicial em dinheiro (`valor_inicial`). No fechamento, `resumir_caixa` consolida as vendas concluídas por forma de pagamento e calcula o `valor_esperado` em dinheiro (`valor_inicial + recebido_em_dinheiro`). Se o `valor_contado` divergir do esperado, uma `justificativa` é obrigatória.

![Diagrama de Sequência: Abertura e Fechamento de Caixa](diagramas/sequencia_caixa.drawio.svg)

*(Arquivo fonte editável: [sequencia_caixa.drawio](diagramas/sequencia_caixa.drawio))*
