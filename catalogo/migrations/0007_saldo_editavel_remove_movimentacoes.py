from django.db import migrations, models


class Migration(migrations.Migration):
    """O saldo passa a ser informado no cadastro e o app de movimentações sai do projeto.

    A tabela de movimentações (do antigo app `estoque`) é apagada aqui para não
    ficar órfã em bancos que já a tinham criado.
    """

    dependencies = [
        ("catalogo", "0006_remove_estoque_minimo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="produto",
            name="saldo_estoque",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Quantidade disponível para venda; diminui automaticamente a cada venda concluída.",
                verbose_name="quantidade em estoque",
            ),
        ),
        migrations.RunSQL(
            sql=[
                "DROP TABLE IF EXISTS estoque_movimentacao",
                "DELETE FROM django_migrations WHERE app = 'estoque'",
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
