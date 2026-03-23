from django import forms

from .models import EstruturaFixacao, Inversor, ModuloFotovoltaico, PropostaSolar


class PropostaSolarForm(forms.ModelForm):
    class Meta:
        model = PropostaSolar
        fields = [
            "cliente",
            "consumo_medio_kwh",
            "hsp",
            "fator_eficiencia",
            "modulo",
            "quantidade_modulos",
            "inversor",
            "estrutura",
            "valor_equipamentos",
            "valor_instalacao",
            "validade",
            "observacoes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"

        self.fields["consumo_medio_kwh"].widget.attrs.update({"placeholder": "Ex: 350", "inputmode": "decimal", "step": "0.01"})
        self.fields["hsp"].widget.attrs.update({"placeholder": "5.50", "inputmode": "decimal", "step": "0.01"})
        self.fields["fator_eficiencia"].widget.attrs.update({"placeholder": "0.75", "inputmode": "decimal", "step": "0.01"})
        self.fields["quantidade_modulos"].widget.attrs.update(
            {
                "placeholder": "Calculado automaticamente",
                "inputmode": "numeric",
                "readonly": True,
                "style": "background: var(--fundo-alt); cursor: not-allowed;",
            }
        )
        self.fields["valor_equipamentos"].widget.attrs.update({"placeholder": "0,00", "inputmode": "decimal", "step": "0.01"})
        self.fields["valor_instalacao"].widget.attrs.update({"placeholder": "0,00", "inputmode": "decimal", "step": "0.01"})
        self.fields["validade"].widget.attrs["type"] = "date"
        self.fields["observacoes"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "rows": "3",
                "placeholder": "Condições comerciais, observações técnicas...",
            }
        )
        self.fields["modulo"].queryset = ModuloFotovoltaico.objects.filter(ativo=True)
        self.fields["inversor"].queryset = Inversor.objects.filter(ativo=True)
        self.fields["estrutura"].queryset = EstruturaFixacao.objects.filter(ativo=True)
