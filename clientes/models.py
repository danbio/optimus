import re

from django.db import models

from core.models import BaseModel


class Cliente(BaseModel):
    TIPO_PF = "PF"
    TIPO_PJ = "PJ"
    TIPO_CHOICES = [
        (TIPO_PF, "Pessoa Física"),
        (TIPO_PJ, "Pessoa Jurídica"),
    ]

    # Identificação
    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES, editable=False, verbose_name="tipo")
    cpf_cnpj = models.CharField(max_length=18, unique=True, verbose_name="CPF / CNPJ")
    nome = models.CharField(max_length=200, verbose_name="nome")
    nome_fantasia = models.CharField(max_length=200, blank=True, verbose_name="nome fantasia")
    rg_ie = models.CharField(max_length=30, blank=True, verbose_name="RG / Inscrição Estadual")
    data_nascimento = models.DateField(null=True, blank=True, verbose_name="data de nascimento")

    # Contato
    telefone = models.CharField(max_length=15, blank=True, verbose_name="telefone")
    celular = models.CharField(max_length=15, blank=True, verbose_name="celular")
    email = models.EmailField(blank=True, verbose_name="e-mail")

    # Endereço
    cep = models.CharField(max_length=9, blank=True, verbose_name="CEP")
    logradouro = models.CharField(max_length=200, blank=True, verbose_name="logradouro")
    numero = models.CharField(max_length=20, blank=True, verbose_name="número")
    complemento = models.CharField(max_length=100, blank=True, verbose_name="complemento")
    bairro = models.CharField(max_length=100, blank=True, verbose_name="bairro")
    cidade = models.CharField(max_length=100, blank=True, verbose_name="cidade")
    estado = models.CharField(max_length=2, blank=True, verbose_name="UF")

    # Outros
    observacoes = models.TextField(blank=True, verbose_name="observações")
    ativo = models.BooleanField(default=True, verbose_name="ativo")

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        digits = re.sub(r"\D", "", self.cpf_cnpj)
        self.tipo = self.TIPO_PF if len(digits) == 11 else self.TIPO_PJ
        super().save(*args, **kwargs)

    @property
    def telefone_principal(self):
        return self.celular or self.telefone

    @property
    def endereco_resumido(self):
        parts = []
        if self.logradouro:
            partes_end = self.logradouro
            if self.numero:
                partes_end += f", {self.numero}"
            parts.append(partes_end)
        if self.bairro:
            parts.append(self.bairro)
        if self.cidade and self.estado:
            parts.append(f"{self.cidade}/{self.estado}")
        elif self.cidade:
            parts.append(self.cidade)
        return " — ".join(parts)
