from datetime import date

from django import forms

from clientes.models import Cliente

from .models import (
    Distribuidora,
    EstruturaFixacao,
    Inversor,
    MateriaisEletricos,
    ModuloFotovoltaico,
    Municipio,
    PrecoEquipamentoSolar,
    PropostaSolar,
)


class PropostaSolarForm(forms.ModelForm):
    class Meta:
        model = PropostaSolar
        fields = [
            "cliente",
            "consumo_medio_kwh",
            "modulo",
            "municipio",
            "hsp",
            "fator_eficiencia",
            "valor_equipamentos_manual",
            "valor_instalacao",
            "distribuidora",
            "tarifa_kwh",
            "tipo_ligacao",
            "autoconsumo_simultaneo_pct",
            "validade",
            "observacoes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"

        self.fields["consumo_medio_kwh"].widget.attrs.update({"placeholder": "Ex: 350", "inputmode": "decimal", "step": "0.01"})
        # "Módulo de referência" alimenta só a calculadora de dimensionamento
        # (endpoint solar:dimensionar via HTMX) — o módulo que efetivamente
        # entra na proposta é o que está na tabela de Itens; se houver um item
        # de categoria Módulo lá, ele tem prioridade sobre este campo no save.
        self.fields["modulo"].queryset = ModuloFotovoltaico.objects.filter(ativo=True)

        # Só municípios com HSP sincronizado: escolher um sem HSP não
        # adiantaria nada e o vendedor não teria como saber disso na tela.
        self.fields["municipio"].required = False
        self.fields["municipio"].queryset = Municipio.objects.filter(hsp_anual__isnull=False)
        self.fields["municipio"].empty_label = "— usar o HSP digitado ao lado —"

        # Proposta nova herda o município do endereço do cliente; o vendedor
        # troca se o gerador for para outro local (sítio, segunda casa...).
        if not self.instance.pk and not self.initial.get("municipio"):
            sugerido = self._municipio_do_cliente()
            if sugerido:
                self.initial["municipio"] = sugerido.pk
                self.initial.setdefault("hsp", sugerido.hsp_anual)

        self.fields["hsp"].widget.attrs.update({"placeholder": "5.50", "inputmode": "decimal", "step": "0.01"})
        self.fields["fator_eficiencia"].widget.attrs.update({"placeholder": "0.75", "inputmode": "decimal", "step": "0.01"})

        self.fields["valor_equipamentos_manual"].required = False
        self.fields["valor_equipamentos_manual"].widget.attrs.update({"placeholder": "0,00", "inputmode": "decimal", "step": "0.01"})
        self.fields["valor_instalacao"].widget.attrs.update({"placeholder": "0,00", "inputmode": "decimal", "step": "0.01"})
        self.fields["distribuidora"].required = False
        self.fields["distribuidora"].queryset = Distribuidora.objects.filter(ativo=True)
        self.fields["distribuidora"].empty_label = "— usar a tarifa digitada abaixo —"
        self.fields["tarifa_kwh"].required = False
        self.fields["tarifa_kwh"].widget.attrs.update({"placeholder": "Ex: 1,385750", "inputmode": "decimal", "step": "0.000001"})
        self.fields["autoconsumo_simultaneo_pct"].widget.attrs.update(
            {"placeholder": "25", "inputmode": "decimal", "step": "1", "min": "0", "max": "100"}
        )
        self.fields["validade"].widget.attrs["type"] = "date"
        self.fields["observacoes"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "rows": "3",
                "placeholder": "Condições comerciais, observações técnicas...",
            }
        )


    def _municipio_do_cliente(self):
        """Casa a cidade escrita no cadastro do cliente com um município.

        O cadastro guarda cidade como texto livre, então o casamento é por
        nome + UF, sem acento e sem caixa. Não achando, devolve None e o
        vendedor escolhe na mão — melhor que arriscar o município errado.
        """
        cliente = self.initial.get("cliente") or getattr(self.instance, "cliente", None)
        if isinstance(cliente, int):
            cliente = Cliente.objects.filter(pk=cliente).first()
        if not cliente or not cliente.cidade or not cliente.estado:
            return None

        return (
            Municipio.objects.filter(
                uf__iexact=cliente.estado.strip(),
                nome__unaccent__iexact=cliente.cidade.strip(),
                hsp_anual__isnull=False,
            ).first()
            if _tem_unaccent()
            else _casar_por_nome(cliente)
        )


def _tem_unaccent() -> bool:
    """`__unaccent` exige a extensão do PostgreSQL; em SQLite não existe."""
    from django.db import connection

    return connection.vendor == "postgresql"


def _casar_por_nome(cliente):
    """Fallback sem `unaccent`: normaliza em Python e compara.

    Roda sobre os municípios da UF do cliente (algumas centenas no pior
    caso), não sobre o país inteiro.
    """
    alvo = _normalizar(cliente.cidade)
    for municipio in Municipio.objects.filter(uf__iexact=cliente.estado.strip(), hsp_anual__isnull=False):
        if _normalizar(municipio.nome) == alvo:
            return municipio
    return None


def _normalizar(texto: str) -> str:
    import unicodedata

    sem_acento = unicodedata.normalize("NFKD", texto.strip())
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).casefold()


class ItemPropostaSolarForm(forms.ModelForm):
    class Meta:
        model = PropostaSolar.itens.field.model  # ItemPropostaSolar
        fields = ["modulo", "inversor", "estrutura", "material", "quantidade"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_form_control(self)
        self.fields["quantidade"].widget.attrs.update({"inputmode": "numeric", "min": "1"})

        # Filtra apenas ativos
        self.fields["modulo"].queryset = ModuloFotovoltaico.objects.filter(ativo=True)
        self.fields["inversor"].queryset = Inversor.objects.filter(ativo=True)
        self.fields["estrutura"].queryset = EstruturaFixacao.objects.filter(ativo=True)
        self.fields["material"].queryset = MateriaisEletricos.objects.filter(ativo=True)


ItemPropostaSolarFormSet = forms.inlineformset_factory(
    PropostaSolar,
    PropostaSolar.itens.field.model,
    form=ItemPropostaSolarForm,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


def _aplicar_form_control(form_instance):
    for field in form_instance.fields.values():
        field.widget.attrs["class"] = "form-control"
        field.widget.attrs["autocomplete"] = "off"


class ModuloFotovoltaicoForm(forms.ModelForm):
    class Meta:
        model = ModuloFotovoltaico
        fields = [
            "fabricante",
            "modelo",
            "potencia_wp",
            "eficiencia",
            "voc",
            "isc",
            "largura",
            "altura",
            "peso",
            "garantia_produto",
            "garantia_desempenho",
            "ativo",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_form_control(self)
        self.fields["potencia_wp"].widget.attrs["placeholder"] = "Ex: 400"
        self.fields["eficiencia"].widget.attrs.update({"placeholder": "Ex: 20.50", "step": "0.01"})
        self.fields["voc"].widget.attrs.update({"placeholder": "Ex: 49.60", "step": "0.01"})
        self.fields["isc"].widget.attrs.update({"placeholder": "Ex: 10.40", "step": "0.01"})
        self.fields["largura"].widget.attrs["placeholder"] = "mm, ex: 1134"
        self.fields["altura"].widget.attrs["placeholder"] = "mm, ex: 2094"
        self.fields["peso"].widget.attrs.update({"placeholder": "kg, ex: 26.5", "step": "0.01"})
        self.fields["garantia_produto"].widget.attrs["placeholder"] = "anos, ex: 12"
        self.fields["garantia_desempenho"].widget.attrs["placeholder"] = "anos, ex: 25"


class InversorForm(forms.ModelForm):
    class Meta:
        model = Inversor
        fields = [
            "fabricante",
            "modelo",
            "potencia_kw",
            "tipo",
            "fase",
            "tensao_max_entrada",
            "quantidade_mppt",
            "garantia",
            "ativo",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_form_control(self)
        self.fields["potencia_kw"].widget.attrs.update({"placeholder": "Ex: 5.00", "step": "0.01"})
        self.fields["tensao_max_entrada"].widget.attrs["placeholder"] = "V, ex: 600"
        self.fields["quantidade_mppt"].widget.attrs["placeholder"] = "Ex: 2"
        self.fields["garantia"].widget.attrs["placeholder"] = "anos, ex: 5"


class EstruturaFixacaoForm(forms.ModelForm):
    class Meta:
        model = EstruturaFixacao
        fields = ["fabricante", "modelo", "tipo", "material", "descricao", "ativo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_form_control(self)
        self.fields["descricao"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "rows": "3",
                "placeholder": "Detalhes técnicos adicionais...",
            }
        )


class MateriaisEletricosForm(forms.ModelForm):
    class Meta:
        model = MateriaisEletricos
        fields = ["fabricante", "modelo", "categoria", "unidade", "descricao", "ativo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_form_control(self)
        self.fields["fabricante"].widget.attrs["placeholder"] = "Ex: Intelbras, Pial, WEG"
        self.fields["modelo"].widget.attrs["placeholder"] = "Ex: Cabo 6mm² preto, DPS 1P+N 40kA"
        self.fields["descricao"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "rows": "3",
                "placeholder": "Especificação técnica detalhada...",
            }
        )


class PrecoEquipamentoSolarForm(forms.ModelForm):
    """Form de preço contextual — os FKs de equipamento são preenchidos pela view,
    não pelo usuário. O form exibe apenas custo, venda e vigência.
    A validação XOR é responsabilidade da view, não do form."""

    class Meta:
        model = PrecoEquipamentoSolar
        fields = ["preco_custo", "preco_venda", "vigente_desde"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_form_control(self)
        self.fields["preco_custo"].widget.attrs.update({"placeholder": "0,00", "step": "0.01", "inputmode": "decimal"})
        self.fields["preco_venda"].widget.attrs.update({"placeholder": "0,00", "step": "0.01", "inputmode": "decimal"})
        self.fields["vigente_desde"].initial = date.today()
        self.fields["vigente_desde"].widget.attrs["type"] = "date"

    def _post_clean(self):
        # Executa a validação normal mas remove o erro de XOR — os FKs de
        # equipamento são atribuídos pela view após save(commit=False).
        super()._post_clean()
        if "__all__" in self._errors:
            filtrados = [e for e in self._errors["__all__"] if "equipamento" not in str(e).lower()]
            del self._errors["__all__"]
            for e in filtrados:
                self.add_error(None, e)
