# trab_eng_soft

Repositório para elaboração do trabalho da cadeira INF01127 - Engenharia de Software.

**Sistema de Controle de Vendas e Estoque da Lojinha do DACOMP**: aplicação web em Python + Django.

## Como executar

```bash
python -m venv .venv
.venv/Scripts/activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py popular_demo --senha <escolha-uma-senha>
python manage.py runserver
```

Acesse http://localhost:8000 e entre com `diretoria`, `bolsista` ou `voluntario` e a senha escolhida.
Para o painel administrativo do Django, crie um superusuário com `python manage.py createsuperuser`.

Testes: `pytest`

## Arquitetura

Monólito Django em camadas, dividido em pacotes por subsistema. Cada pacote segue
`models.py` (entidades) → `servicos.py` (regras de negócio) → `forms.py`/`views.py` (controle) → `templates/` (apresentação).

| Pacote     | Responsabilidade                                            | Casos de uso        |
|------------|-------------------------------------------------------------|---------------------|
| `contas`   | Autenticação, perfis fixos (Diretoria, Bolsista, Voluntário) e contas da equipe | UC43, Manter Contas |
| `catalogo` | Cadastro e pesquisa de produtos e serviços                   | UC47, UC05          |
| `estoque`  | Entradas, ajustes e histórico de movimentações               | UC23 (UC24, UC25), UC29 |
| `vendas`   | PDV, abertura e fechamento de caixa, pagamento e consulta de vendas | UC01, UC02, UC03, UC12, UC49 |
| `nucleo`   | Página inicial, formatação, paginação e dados de demonstração | —                   |
| `config`   | Configurações e rotas do projeto                              | —                   |

Dependências: `vendas → estoque → catalogo → contas`; `nucleo` usa todos. O saldo de um produto só é
alterado pelo `estoque.servicos` (entradas, ajustes e baixas de venda), sempre junto com o registro da
movimentação. Ao concluir uma venda, venda, pagamento e baixa de estoque são gravados em uma única
transação (RNF01). As listagens usam 10 registros por página.

### PDV

Em **Vendas → PDV**: abra o caixa, leia o código de barras (ou digite o código ou parte do nome) e
pressione Enter para incluir itens. `F2` volta ao campo de produto e `F4` finaliza a venda. Na
finalização, escolha a forma de pagamento; em dinheiro, o sistema calcula o troco. O fechamento do
caixa confere as vendas por forma de pagamento e exige justificativa quando o valor contado difere do
esperado.

Próximo pacote previsto: `relatorios` (UC50).
