from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from clientes.models import Cliente

            ctx["total_clientes"] = Cliente.objects.filter(ativo=True).count()
        except Exception:
            ctx["total_clientes"] = "—"

        try:
            from solar.models import PropostaSolar

            ctx["total_propostas_solar"] = PropostaSolar.objects.exclude(status="cancelada").count()
        except Exception:
            ctx["total_propostas_solar"] = "—"

        try:
            from ordens_servico.models import OrdemServico

            ctx["total_os_abertas"] = OrdemServico.objects.exclude(status__in=["concluida", "faturada"]).count()
        except Exception:
            ctx["total_os_abertas"] = "—"

        return ctx
