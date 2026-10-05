from django.db import migrations

# Cópia fixa dos nomes em contas.perfis: migrações não devem importar código da aplicação.
NOMES_PERFIS = ("Diretoria", "Bolsista", "Voluntário")


def criar_perfis(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nome in NOMES_PERFIS:
        Group.objects.get_or_create(name=nome)


def remover_perfis(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=NOMES_PERFIS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("contas", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(criar_perfis, remover_perfis)]
