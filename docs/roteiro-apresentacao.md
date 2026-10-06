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

Deixe claro que o pagamento é confirmado pelo operador, sem integração bancária. As consultas já funcionam; UC50, geração de relatórios básicos, fica para a Etapa 3. Devoluções, emissão fiscal, carteirinhas, empréstimos e os demais módulos do antigo mini-ERP ficaram fora do recorte.

No slide 8, passe para o navegador. Como referência para o ensaio, reserve cerca de um terço do tempo para a explicação e dois terços para a demonstração. Ajuste a duração ao tempo definido pela professora.

## Demonstração ao vivo

1. **Consultar e abrir o caixa — UC05, UC28 e UC01.** Pesquise `AGU-500` em Produtos e confira o saldo. Na base recém-populada, a água custa R$ 3,00 e tem 36 unidades. Abra o caixa com R$ 50,00 em dinheiro. Mostre que o atendimento fica associado ao operador.
2. **Registrar a venda e receber — UC03 e UC12.** No PDV, adicione duas águas e um café pequeno (`CAF-P`). Confira o total de R$ 8,50. Finalize em dinheiro, informe R$ 10,00 e confirme o recebimento. O resumo deve mostrar troco de R$ 1,50. Explique que o café está cadastrado sem controle de estoque.
3. **Conferir e movimentar o estoque — UC29, UC23 e UC24.** Em Estoque, filtre pela água. A baixa da venda deve mostrar 36 → 34, com variação de -2 e identificação do responsável. Registre uma entrada de cinco águas, revise e confirme: o saldo passa de 34 para 39. Abra os detalhes da movimentação. Se o saldo inicial for outro, use o valor consultado e acompanhe as mesmas variações.
4. **Consultar vendas e fechar o caixa — UC49 e UC02.** Abra a consulta de vendas e os detalhes da venda realizada. No fechamento, confira os totais por forma de pagamento e o dinheiro esperado. Se esta foi a única venda do caixa, o esperado é R$ 58,50. Informe esse valor, revise e confirme. Mostre o caixa fechado.

Se houver tempo, apresente um ajuste de contagem, com motivo, ou o bloqueio de um produto sem saldo. Esses exemplos são complementares e podem ficar para as perguntas.

## Conferência antes da aula

- Iniciar a aplicação e o PostgreSQL na máquina que será usada na apresentação.
- Executar os testes nesse ambiente e ensaiar o roteiro completo.
- Conferir login, saldo inicial, caixa fechado e acesso aos arquivos da entrega.
- Abrir os slides e o sistema antes de começar a exposição.
- Demonstrar o sistema ao vivo. O enunciado não permite substituir a demonstração por vídeo.

Na revisão da Etapa 2, os 50 testes passaram em um banco SQLite separado. A execução com PostgreSQL pelo Docker precisa ser conferida na máquina da apresentação, pois o Docker Desktop do ambiente de revisão apresentou uma falha de inicialização.
