import datetime

from django import forms
from django.forms import inlineformset_factory

from .models import ItemProduto, ItemServico, PropostaServico, Servico


class ServicoForm(forms.ModelForm):
    class Meta:
        model = Servico
        fields = ["nome", "tipo", "descricao", "ativo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
        self.fields["descricao"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "rows": "3",
                "placeholder": "Descrição do serviço (opcional)...",
            }
        )


class PropostaServicoForm(forms.ModelForm):
    class Meta:
        model = PropostaServico
        fields = ["cliente", "tipo_servico", "validade", "observacoes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
        self.fields["validade"].widget.attrs["type"] = "date"
        self.fields["observacoes"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "rows": "3",
                "placeholder": "Condições comerciais, observações técnicas...",
            }
        )

    def get_initial_for_field(self, field, field_name):
        if field_name == "validade" and not self.initial.get("validade"):
            return datetime.date.today() + datetime.timedelta(days=30)
        return super().get_initial_for_field(field, field_name)


class ItemServicoForm(forms.ModelForm):
    class Meta:
        model = ItemServico
        fields = ["servico", "valor"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
        self.fields["valor"].widget.attrs.update({"inputmode": "decimal", "step": "0.01", "placeholder": "0,00"})
        self.fields["servico"].queryset = Servico.objects.filter(ativo=True)


class ItemProdutoForm(forms.ModelForm):
    class Meta:
        model = ItemProduto
        fields = ["produto", "quantidade", "valor_unitario"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
        self.fields["quantidade"].widget.attrs.update({"inputmode": "numeric", "min": "1"})
        self.fields["valor_unitario"].widget.attrs.update({"inputmode": "decimal", "step": "0.01", "placeholder": "0,00"})


ItemServicoFormSet = inlineformset_factory(
    PropostaServico,
    ItemServico,
    form=ItemServicoForm,
    extra=1,
    can_delete=True,
)

ItemProdutoFormSet = inlineformset_factory(
    PropostaServico,
    ItemProduto,
    form=ItemProdutoForm,
    extra=1,
    can_delete=True,
)
