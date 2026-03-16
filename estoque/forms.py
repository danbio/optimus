from django import forms

from .models import Produto


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = [
            "codigo",
            "descricao",
            "bu",
            "segmento",
            "familia",
            "ipi",
            "icms",
            "ncm",
            "ean",
            "psd",
            "pscf",
            "preco_referencia",
            "qtd_multipla",
            "observacoes",
            "ativo",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ("ativo", "preco_referencia"):
                field.widget.attrs["class"] = "form-control"
                field.widget.attrs["autocomplete"] = "off"

        self.fields["preco_referencia"].widget.attrs["class"] = "form-control"
        self.fields["codigo"].widget.attrs.update({"placeholder": "Código Intelbras", "inputmode": "numeric"})
        self.fields["descricao"].widget.attrs["placeholder"] = "Descrição completa do produto"
        self.fields["bu"].widget.attrs["placeholder"] = "Ex: BU SEGURANCA"
        self.fields["segmento"].widget.attrs["placeholder"] = "Ex: CFTV IP"
        self.fields["familia"].widget.attrs["placeholder"] = "Ex: Câmeras IP"
        self.fields["ncm"].widget.attrs["placeholder"] = "0000.00.00"
        self.fields["ean"].widget.attrs["placeholder"] = "Código EAN/GTIN"
        self.fields["psd"].widget.attrs.update({"placeholder": "0,00", "inputmode": "decimal"})
        self.fields["pscf"].widget.attrs.update({"placeholder": "0,00", "inputmode": "decimal"})
        self.fields["qtd_multipla"].widget.attrs.update({"placeholder": "1", "inputmode": "decimal"})
        self.fields["observacoes"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "rows": "3",
                "placeholder": "Observações sobre o produto...",
            }
        )
        self.fields["ativo"].widget = forms.CheckboxInput()


class ImportarPlanilhaForm(forms.Form):
    arquivo = forms.FileField(
        label="Planilha de preços",
        help_text="Formatos aceitos: .xlsb, .xlsx, .xls",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["arquivo"].widget.attrs.update({"class": "form-control", "accept": ".xlsb,.xlsx,.xls"})

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get("arquivo")
        if arquivo:
            nome = arquivo.name.lower()
            if not any(nome.endswith(ext) for ext in (".xlsb", ".xlsx", ".xls")):
                raise forms.ValidationError("Formato inválido. Use .xlsb, .xlsx ou .xls.")
            if arquivo.size > 50 * 1024 * 1024:
                raise forms.ValidationError("Arquivo muito grande. Tamanho máximo: 50 MB.")
        return arquivo
