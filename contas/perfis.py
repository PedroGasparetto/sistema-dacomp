"""Perfis fixos de acesso (seção C.2 do relatório).

Os perfis são grupos do Django, o que permite o acúmulo de papéis: um
integrante da Diretoria pode também atuar como Bolsista.
"""

DIRETORIA = "Diretoria"
BOLSISTA = "Bolsista"
VOLUNTARIO = "Voluntário"

TODOS_PERFIS = (DIRETORIA, BOLSISTA, VOLUNTARIO)

# "Operador" nos casos de uso: atividades comuns aos três perfis.
PERFIS_OPERADOR = TODOS_PERFIS
PERFIS_GESTAO_PRODUTOS = (DIRETORIA, BOLSISTA)
PERFIS_GESTAO_CONTAS = (DIRETORIA,)


def possui_algum_perfil(usuario, perfis_permitidos):
    if not usuario.is_authenticated:
        return False
    if usuario.is_superuser:
        return True
    return usuario.groups.filter(name__in=perfis_permitidos).exists()
