from django import forms

from .models import Chamado, InteracaoChamado


class ChamadoForm(forms.ModelForm):
    class Meta:
        model = Chamado
        fields = [
            "cliente",
            "tipo",
            "prioridade",
            "assunto",
            "descricao",
            "responsavel",
            "prazo",
            "ordem_servico",
            "proposta_solar",
            "proposta_servico",
            "venda_balcao",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"

        self.fields["prazo"].widget.attrs["type"] = "date"
        self.fields["descricao"].widget = forms.Textarea(
            attrs={"class": "form-control", "autocomplete": "off", "rows": "4", "placeholder": "Descreva o problema ou solicitação..."}
        )
        self.fields["ordem_servico"].required = False
        self.fields["proposta_solar"].required = False
        self.fields["proposta_servico"].required = False
        self.fields["venda_balcao"].required = False
        self.fields["responsavel"].required = False
        self.fields["prazo"].required = False

        # Só mostra origens ativas/relevantes
        from balcao.models import Venda
        from ordens_servico.models import OrdemServico
        from servicos.models import PropostaServico
        from solar.models import PropostaSolar

        self.fields["ordem_servico"].queryset = OrdemServico.objects.select_related("cliente").order_by("-criado_em")[:200]
        self.fields["proposta_solar"].queryset = PropostaSolar.objects.select_related("cliente").order_by("-criado_em")[:200]
        self.fields["proposta_servico"].queryset = PropostaServico.objects.select_related("cliente").order_by("-criado_em")[:200]
        self.fields["venda_balcao"].queryset = Venda.objects.filter(status="finalizada").select_related("cliente").order_by("-criado_em")[:200]


class InteracaoForm(forms.ModelForm):
    class Meta:
        model = InteracaoChamado
        fields = ["tipo", "texto"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"
        self.fields["texto"].widget = forms.Textarea(
            attrs={"class": "form-control", "autocomplete": "off", "rows": "3", "placeholder": "Descreva a interação..."}
        )
