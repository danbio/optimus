import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Cliente


def _validar_cpf(cpf: str) -> bool:
    cpf = re.sub(r"\D", "", cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto in (10, 11):
        resto = 0
    if resto != int(cpf[9]):
        return False
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto in (10, 11):
        resto = 0
    return resto == int(cpf[10])


def _validar_cnpj(cnpj: str) -> bool:
    cnpj = re.sub(r"\D", "", cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def _digito(base: str) -> int:
        n = len(base)
        soma, pos = 0, n - 7
        for i in range(n, 0, -1):
            soma += int(base[n - i]) * pos
            pos -= 1
            if pos < 2:
                pos = 9
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    return int(cnpj[12]) == _digito(cnpj[:12]) and int(cnpj[13]) == _digito(cnpj[:13])


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "cpf_cnpj",
            "nome",
            "nome_fantasia",
            "rg_ie",
            "data_nascimento",
            "telefone",
            "celular",
            "email",
            "cep",
            "logradouro",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
            "observacoes",
            "ativo",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "ativo":
                field.widget.attrs["class"] = "form-control"
                field.widget.attrs["autocomplete"] = "off"

        self.fields["cpf_cnpj"].widget.attrs.update(
            {
                "placeholder": "000.000.000-00 ou 00.000.000/0001-00",
                "maxlength": "18",
                "id": "id_cpf_cnpj",
                "inputmode": "numeric",
            }
        )
        self.fields["nome"].widget.attrs["placeholder"] = "Nome completo ou razão social"
        self.fields["nome_fantasia"].widget.attrs["placeholder"] = "Nome fantasia"
        self.fields["rg_ie"].widget.attrs["placeholder"] = "RG ou Inscrição Estadual"
        self.fields["data_nascimento"].widget.attrs["type"] = "date"
        self.fields["telefone"].widget.attrs.update(
            {
                "placeholder": "(00) 0000-0000",
                "maxlength": "14",
                "inputmode": "numeric",
            }
        )
        self.fields["celular"].widget.attrs.update(
            {
                "placeholder": "(00) 00000-0000",
                "maxlength": "15",
                "inputmode": "numeric",
            }
        )
        self.fields["email"].widget.attrs["placeholder"] = "email@exemplo.com"
        self.fields["email"].widget.attrs["type"] = "email"
        self.fields["cep"].widget.attrs.update(
            {
                "placeholder": "00000-000",
                "maxlength": "9",
                "id": "id_cep",
                "inputmode": "numeric",
            }
        )
        self.fields["numero"].widget.attrs["placeholder"] = "Nº"
        self.fields["complemento"].widget.attrs["placeholder"] = "Apto, sala, bloco..."
        self.fields["estado"].widget.attrs.update({"maxlength": "2", "placeholder": "UF"})
        self.fields["observacoes"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "rows": "3",
                "placeholder": "Informações adicionais sobre o cliente...",
            }
        )
        self.fields["ativo"].widget = forms.CheckboxInput()

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        return email

    def clean_cpf_cnpj(self):
        valor = self.cleaned_data.get("cpf_cnpj", "")
        digits = re.sub(r"\D", "", valor)
        if len(digits) == 11:
            if not _validar_cpf(digits):
                raise ValidationError("CPF inválido. Verifique os dígitos informados.")
        elif len(digits) == 14:
            if not _validar_cnpj(digits):
                raise ValidationError("CNPJ inválido. Verifique os dígitos informados.")
        else:
            raise ValidationError("Informe um CPF (11 dígitos) ou CNPJ (14 dígitos) válido.")
        return valor
