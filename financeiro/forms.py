from django import forms
from django.utils import timezone

from .models import BaixaFinanceira, LancamentoFinanceiro


class LancamentoForm(forms.ModelForm):
    class Meta:
        model = LancamentoFinanceiro
        fields = [
            "cliente",
            "descricao",
            "valor_bruto",
            "desconto",
            "forma_pagamento",
            "num_parcelas",
            "data_vencimento",
            "observacoes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"

        self.fields["data_vencimento"].widget.attrs["type"] = "date"
        self.fields["valor_bruto"].widget.attrs.update({"inputmode": "decimal", "step": "0.01", "placeholder": "0,00"})
        self.fields["desconto"].widget.attrs.update({"inputmode": "decimal", "step": "0.01", "placeholder": "0,00"})
        self.fields["num_parcelas"].widget.attrs.update({"min": "1", "max": "60"})
        self.fields["observacoes"].widget = forms.Textarea(attrs={"class": "form-control", "autocomplete": "off", "rows": "3"})

    def clean(self):
        cleaned = super().clean()
        valor_bruto = cleaned.get("valor_bruto") or 0
        desconto = cleaned.get("desconto") or 0
        if desconto > valor_bruto:
            self.add_error("desconto", "O desconto não pode ser maior que o valor bruto.")
        return cleaned


class BaixaForm(forms.ModelForm):
    class Meta:
        model = BaixaFinanceira
        fields = ["valor", "forma_pagamento", "data_pagamento", "parcela", "observacao"]

    def __init__(self, *args, lancamento=None, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"

        self.fields["data_pagamento"].widget.attrs["type"] = "date"
        self.fields["data_pagamento"].initial = timezone.localdate()
        self.fields["valor"].widget.attrs.update({"inputmode": "decimal", "step": "0.01", "placeholder": "0,00"})
        self.fields["observacao"].widget.attrs["placeholder"] = "Observação opcional..."

        if lancamento:
            self.fields["parcela"].queryset = lancamento.parcelas.filter(status="pendente")
            self.fields["valor"].initial = lancamento.saldo_aberto
        else:
            self.fields["parcela"].queryset = BaixaFinanceira._meta.get_field("parcela").related_model.objects.none()

    def clean_valor(self):
        valor = self.cleaned_data.get("valor")
        if valor is not None and valor <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return valor
