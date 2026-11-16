from .perfis import PERFIS_GESTAO_CONTAS, PERFIS_GESTAO_PRODUTOS, PERFIS_OPERADOR, TODOS_PERFIS


def perfis(request):
    usuario = request.user
    if not usuario.is_authenticated:
        return {}

    grupos = set(usuario.groups.values_list("name", flat=True))

    def permitido(perfis_permitidos):
        return usuario.is_superuser or bool(grupos.intersection(perfis_permitidos))

    return {
        "perfis_usuario": [perfil for perfil in TODOS_PERFIS if perfil in grupos],
        "eh_operador": permitido(PERFIS_OPERADOR),
        "pode_gerir_produtos": permitido(PERFIS_GESTAO_PRODUTOS),
        "pode_gerir_contas": permitido(PERFIS_GESTAO_CONTAS),
    }
