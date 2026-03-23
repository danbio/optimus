from django import forms

from .models import ItemVenda, Venda


class VendaHeaderForm(forms.ModelForm):
    class Meta:
        model = Venda
        fields = ["cliente", "cliente_nome_avulso", "desconto_reais", "desconto_pct", "forma_pagamento", "num_parcelas", "observacoes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"

        self.fields["cliente"].required = False
        self.fields["cliente_nome_avulso"].widget.attrs["placeholder"] = "Nome do cliente (sem cadastro)..."
        self.fields["desconto_reais"].widget.attrs.update({"inputmode": "decimal", "step": "0.01", "placeholder": "0,00", "id": "id_desconto_reais"})
        self.fields["desconto_pct"].widget.attrs.update({"inputmode": "decimal", "step": "0.01", "placeholder": "0,00", "id": "id_desconto_pct"})
        self.fields["num_parcelas"].widget.attrs.update({"min": "1", "max": "60"})
        self.fields["observacoes"].widget = forms.Textarea(
            attrs={"class": "form-control", "autocomplete": "off", "rows": "2", "placeholder": "Observações opcionais..."}
        )


class ItemVendaForm(forms.ModelForm):
    class Meta:
        model = ItemVenda
        fields = ["produto", "quantidade", "valor_unitario", "desconto_item"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from estoque.models import Produto

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"

        self.fields["produto"].queryset = Produto.objects.filter(ativo=True).only("pk", "descricao", "codigo")
        self.fields["quantidade"].widget.attrs.update({"inputmode": "decimal", "step": "0.01", "min": "0.01", "placeholder": "1"})
        self.fields["valor_unitario"].widget.attrs.update({"inputmode": "decimal", "step": "0.01", "placeholder": "0,00"})
        self.fields["desconto_item"].widget.attrs.update({"inputmode": "decimal", "step": "0.01", "placeholder": "0,00"})
