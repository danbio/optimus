<#
.SYNOPSIS
    Verificação completa do ERP Optimus antes de commitar.
.DESCRIPTION
    Executa lint, testes, check de migrations e deploy check em sequência.
    Se qualquer etapa falhar, interrompe e reporta o erro.
#>

param(
    [switch]$Quick  # Pula testes e deploy check (só lint + migrations)
)

$ErrorActionPreference = "Continue"
$global:exitCode = 0

function Write-Step($step, $description) {
    Write-Host "`n[$step] $description" -ForegroundColor Cyan
    Write-Host ("-" * 60) -ForegroundColor DarkGray
}

function Write-Pass($message) {
    Write-Host "  PASS  $message" -ForegroundColor Green
}

function Write-Fail($message) {
    Write-Host "  FAIL  $message" -ForegroundColor Red
    $global:exitCode = 1
}

# Ensure venv Python is used if available
if (Test-Path ".venv\Scripts\activate.ps1") {
    . .venv\Scripts\activate.ps1
}

# 1. Ruff lint
Write-Step "1/4" "Ruff - lint"
try {
    ruff check .
    if ($LASTEXITCODE -eq 0) { Write-Pass 'Sem violacoes' }
    else { Write-Fail 'Violacoes encontradas' }
} catch {
    Write-Fail 'Ruff nao encontrado. Instale: pip install ruff'
}

# 2. Migrations check
Write-Step "2/4" "Django - migrations pendentes"
try {
    python manage.py makemigrations --check --dry-run 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Pass 'Nenhuma migration pendente' }
    else { Write-Fail 'Ha alteracoes em models sem migration. Rode: python manage.py makemigrations' }
} catch {
    Write-Fail 'Erro ao verificar migrations'
}

if ($Quick) {
    Write-Host "`n[--Quick] Pulando testes e deploy check." -ForegroundColor Yellow
    exit $global:exitCode
}

# 3. Testes
Write-Step "3/4" "Django - testes"
try {
    python manage.py test --verbosity=1
    if ($LASTEXITCODE -eq 0) { Write-Pass 'Todos os testes passaram' }
    else { Write-Fail 'Testes falharam' }
} catch {
    Write-Fail 'Erro ao executar testes'
}

# 4. Deploy check
Write-Step "4/4" "Django - check --deploy"
try {
    python manage.py check --deploy
    if ($LASTEXITCODE -eq 0) { Write-Pass 'Deploy check OK' }
    else { Write-Fail 'Deploy check encontrou problemas' }
} catch {
    Write-Fail 'Erro ao executar check --deploy'
}

# Resultado final
Write-Host "`n" ("-" * 60) -ForegroundColor DarkGray
if ($global:exitCode -eq 0) {
    Write-Host "  RESULTADO: Tudo OK - pode commitar!" -ForegroundColor Green
} else {
    Write-Host "  RESULTADO: Corrija os erros acima antes de commitar." -ForegroundColor Red
}
exit $global:exitCode
