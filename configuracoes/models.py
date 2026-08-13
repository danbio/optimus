from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import BaseModel


class Configuracao(BaseModel):
    """Parâmetros de regra de negócio ajustáveis pelo Administrador, sem
    precisar mexer em código.

    Singleton: sempre existe exatamente uma linha (pk=1). Use
    `Configuracao.atual()` para ler — nunca `Configuracao.objects.get(...)`
    diretamente, ele cria a linha padrão na primeira vez que for preciso.
    """

    desconto_maximo_balcao_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("20.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        verbose_name="desconto máximo no balcão (%)",
        help_text=(
            "Desconto efetivo máximo (soma de todos os descontos da venda, "
            "por item e no total) que um Vendedor pode aplicar sozinho no "
            "balcão. O grupo Administrador não é limitado por este valor."
        ),
    )

    inversor_sobrecarga_minima_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("80.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("500"))],
        verbose_name="relação CC:CA mínima aceita (%)",
        help_text=(
            "Abaixo desse percentual (potência do sistema ÷ potência do "
            "inversor), o inversor é marcado como incompatível na proposta "
            "solar por estar superdimensionado para o sistema."
        ),
    )
    inversor_sobrecarga_maxima_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("135.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("500"))],
        verbose_name="relação CC:CA máxima aceita (%)",
        help_text=(
            "Acima desse percentual, o inversor é marcado como incompatível "
            "por sobrecarga (clipping excessivo). 100% = potência do "
            "sistema igual à do inversor; a faixa padrão (80%–135%) segue a "
            "prática usual do mercado solar brasileiro."
        ),
    )

    class Meta:
        verbose_name = "configuração"
        verbose_name_plural = "configurações"

    def __str__(self) -> str:
        return "Configurações do sistema"

    def clean(self) -> None:
        if (
            self.inversor_sobrecarga_minima_pct is not None
            and self.inversor_sobrecarga_maxima_pct is not None
            and self.inversor_sobrecarga_minima_pct >= self.inversor_sobrecarga_maxima_pct
        ):
            raise ValidationError(
                {"inversor_sobrecarga_maxima_pct": "Deve ser maior que a relação mínima."}
            )

    def save(self, *args, **kwargs) -> None:
        # Só força INSERT quando a linha 1 realmente ainda não existe. Sem essa
        # checagem no banco, uma instância nova (self._state.adding=True) que
        # chegue aqui DEPOIS que a linha 1 já existe — ex.: alguém faz
        # Configuracao(...).save() em vez de usar atual() — colidiria (UNIQUE
        # constraint) tentando inserir um pk que já está ocupado.
        #
        # E sem forçar em algum momento, a primeira gravação vira um UPDATE
        # (porque self.pk=1 já está setado abaixo) contra uma linha inexistente:
        # 0 linhas afetadas, e o fallback do Django para INSERT reaproveita os
        # valores já preparados como se fosse update — deixando criado_em
        # (auto_now_add do BaseModel) nulo, o que viola a constraint NOT NULL.
        if self._state.adding and not Configuracao.objects.filter(pk=1).exists():
            kwargs.setdefault("force_insert", True)
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> None:
        raise ValidationError("A configuração do sistema não pode ser excluída.")

    @classmethod
    def atual(cls) -> "Configuracao":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
