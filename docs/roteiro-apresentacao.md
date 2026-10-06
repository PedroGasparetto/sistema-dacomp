# Roteiro da apresentação da Etapa 2

A apresentação começa com uma explicação breve do negócio, do recorte e da arquitetura. A maior parte do tempo fica para usar o sistema ao vivo. Os valores abaixo pertencem aos dados de demonstração.

## Preparação

Na pasta do projeto, com o Docker Desktop funcionando, execute:

```bash
docker compose up --build -d
docker compose exec web python manage.py popular_demo --senha "SUA-SENHA-DE-DEMONSTRACAO"
docker compose exec web pytest
```

Substitua a senha do exemplo por uma senha escolhida para a demonstração. O comando de população cria as contas `diretoria`, `bolsista` e `voluntario`. Se elas já existirem, atualiza as senhas e os perfis dessas contas. Use uma base própria para a apresentação.

Abra http://localhost:8000 e entre como `bolsista`. Confira o caixa e o saldo antes de começar. O comando de população não apaga vendas anteriores nem repõe o saldo de produtos já cadastrados.

## Explicação inicial

Use os slides 1 a 7 para apresentar o atendimento da lojinha, os três perfis fixos, as simplificações e a arquitetura. Explique que a aplicação é um monólito Django em camadas: as telas conduzem o atendimento, os serviços concentram as regras e os modelos mantêm os dados. O diagrama de pacotes mostra como essas responsabilidades se relacionam.

Deixe claro que o pagamento é confirmado pelo operador, sem integração bancária. Na Etapa 2, o saldo é informado diretamente no cadastro e reduzido nas vendas, sem entradas, ajustes ou histórico de movimentações. Contas e perfis são preparados pelo terminal. UC09 a UC12, a interface de UC15, os dois relatórios de UC14 (Vendas e Posição de Estoque) e UC16 Registrar Devolução estão modelados para a Etapa 3. A demonstração apresenta as funcionalidades disponíveis. Emissão fiscal, carteirinhas, empréstimos e os demais módulos do antigo mini-ERP ficaram fora do recorte.

No slide 8, passe para o navegador. Como referência para o ensaio, reserve cerca de um terço do tempo para a explicação e dois terços para a demonstração. Ajuste a duração ao tempo definido pela professora.

## Demonstração ao vivo

1. **Consultar e abrir o caixa — UC02, UC08 e UC03.** Em Produtos, escolha **Código interno** no campo **Pesquisar por**, pesquise `AGU-500` e confira o saldo. Na base recém-populada, a água custa R$ 3,00 e tem 36 unidades. Abra o caixa com R$ 50,00 em dinheiro. Mostre que o atendimento fica associado ao operador.
2. **Registrar a venda e receber — UC05 e UC06.** No PDV, adicione duas águas e um café pequeno (`CAF-P`). Confira o total de R$ 8,50. Finalize em dinheiro, informe R$ 10,00 e confirme o recebimento. O resumo deve mostrar troco de R$ 1,50. Explique que o café está cadastrado sem controle de estoque.
3. **Conferir o saldo — UC02 e UC08.** Volte a Produtos, pesquise `AGU-500` pelo código interno e abra os detalhes. Se o saldo inicial era 36, ele deve ser 34 após a venda. A redução de duas unidades é automática. Não há uma tela de movimentações nesta etapa. Se o saldo inicial for outro, acompanhe a mesma redução de duas unidades.
4. **Consultar vendas e fechar o caixa — UC07 e UC04.** Abra a consulta de vendas e os detalhes da venda realizada. No fechamento, confira os totais por forma de pagamento e o dinheiro esperado. Se esta foi a única venda do caixa, o esperado é R$ 58,50. Informe esse valor, revise e confirme. Mostre o caixa fechado.

Se houver tempo, mostre o bloqueio de um produto sem saldo ou a edição de um produto por Diretoria ou Bolsista (UC13). Nessa tela, a quantidade disponível pode ser informada diretamente. O Voluntário consulta o catálogo e opera vendas e caixa, mas não altera os produtos. Esses exemplos são complementares e podem ficar para as perguntas.

## Conferência antes da aula

- Iniciar a aplicação e o PostgreSQL na máquina que será usada na apresentação.
- Executar os testes nesse ambiente e ensaiar o roteiro completo.
- Conferir login, saldo inicial, caixa fechado e acesso aos arquivos da entrega.
- Abrir os slides e o sistema antes de começar a exposição.
- Demonstrar o sistema ao vivo. O enunciado não permite substituir a demonstração por vídeo.

Na revisão da versão atual da Etapa 2, os 42 testes passaram com PostgreSQL 17 no Docker. A verificação do Django não apontou problemas e não há alterações de modelos sem migração. O roteiro foi conferido no navegador em uma base separada: venda de R$ 8,50, troco de R$ 1,50, redução de duas águas no catálogo e fechamento com R$ 58,50, sem diferença. Antes da aula, ensaie na máquina da apresentação e confira os dados iniciais, pois repetir o roteiro altera o saldo e mantém o histórico de vendas.
