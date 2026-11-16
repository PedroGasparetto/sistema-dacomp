from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from .models import Usuario
from .perfis import DIRETORIA, TODOS_PERFIS


def _campo_perfis():
    return forms.ModelMultipleChoiceField(
        label="Perfis",
        queryset=Group.objects.filter(name__in=TODOS_PERFIS).order_by("name"),
        widget=forms.CheckboxSelectMultiple,
        help_text="Uma pessoa pode acumular perfis, como Diretoria e Bolsista.",
    )


class FormularioCriacaoConta(UserCreationForm):
    perfis = _campo_perfis()

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("username", "first_name", "last_name", "email")

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        if commit:
            usuario.groups.set(self.cleaned_data["perfis"])
        return usuario


class FormularioEdicaoConta(forms.ModelForm):
    perfis = _campo_perfis()

    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email", "is_active")

    def __init__(self, *args, usuario_atuante, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_atuante = usuario_atuante
        self.fields["perfis"].initial = self.instance.groups.filter(name__in=TODOS_PERFIS)

    def clean(self):
        dados = super().clean()
        if self.instance.pk == self.usuario_atuante.pk:
            if not dados.get("is_active", True):
                self.add_error("is_active", "Você não pode desativar a própria conta.")
            perfis = dados.get("perfis")
            if (
                perfis is not None
                and not self.usuario_atuante.is_superuser
                and not perfis.filter(name=DIRETORIA).exists()
            ):
                self.add_error("perfis", "Você não pode remover o próprio perfil de Diretoria.")
        return dados

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        if commit:
            usuario.groups.set(self.cleaned_data["perfis"])
        return usuario
