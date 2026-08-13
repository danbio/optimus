from django import forms

from .models import Configuracao


class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        fields = ["desconto_maximo_balcao_pct"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["autocomplete"] = "off"

        self.fields["desconto_maximo_balcao_pct"].widget.attrs.update(
            {"inputmode": "decimal", "step": "0.01", "min": "0", "max": "100"}
        )
