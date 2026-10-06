from django.contrib.auth import views as auth_views
from django.urls import path

app_name = "contas"

# Contas e senhas são administradas pela linha de comando (criar_conta e changepassword).
urlpatterns = [
    path("entrar/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="entrar"),
    path("sair/", auth_views.LogoutView.as_view(), name="sair"),
]
