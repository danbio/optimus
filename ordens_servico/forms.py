from django import forms
from django.forms import inlineformset_factory

from .models import FotoOS, ItemChecklist, OrdemServico, Tecnico


class TecnicoForm(forms.ModelForm):
    class Meta:
        model = Tecnico
        fields = ["nome", "telefone", "email", "especialidade", "ativo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"


class OrdemServicoForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = [
            "cliente",
            "proposta_solar",
            "proposta_servico",
            "tecnico",
            "prioridade",
            "descricao",
            "observacoes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"

        self.fields["tecnico"].queryset = Tecnico.objects.filter(ativo=True)
        self.fields["descricao"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "rows": "3",
                "placeholder": "Descreva o serviço a ser realizado...",
            }
        )
        self.fields["observacoes"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "rows": "3",
                "placeholder": "Observações adicionais...",
            }
        )

        # Filtrar apenas propostas aprovadas
        from servicos.models import PropostaServico
        from solar.models import PropostaSolar

        self.fields["proposta_solar"].queryset = PropostaSolar.objects.filter(status="aprovada").select_related("cliente")
        self.fields["proposta_servico"].queryset = PropostaServico.objects.filter(status="aprovada").select_related("cliente")


class AssinaturaForm(forms.Form):
    assinatura_nome = forms.CharField(
        max_length=200,
        label="Nome de quem assinou",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "placeholder": "Nome completo...",
            }
        ),
    )
    assinatura_confirmada = forms.BooleanField(
        label="Confirmo a conclusão do serviço",
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )


class ItemChecklistForm(forms.ModelForm):
    class Meta:
        model = ItemChecklist
        fields = ["descricao", "concluido", "observacao"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
        self.fields["concluido"].widget.attrs["class"] = "form-check-input"


ItemChecklistFormSet = inlineformset_factory(
    OrdemServico,
    ItemChecklist,
    form=ItemChecklistForm,
    extra=1,
    can_delete=True,
)


class FotoOSForm(forms.ModelForm):
    class Meta:
        model = FotoOS
        fields = ["foto", "legenda"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
        self.fields["foto"].widget.attrs["accept"] = "image/*"
