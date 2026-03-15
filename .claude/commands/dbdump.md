Cria backup timestamped do banco SQLite de desenvolvimento.

Use este comando ANTES de qualquer `/migrate` em banco com dados reais de teste.

Execute no diretório raiz do projeto (onde fica `db.sqlite3`):

```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$dest = "db.sqlite3.bak_$timestamp"
Copy-Item db.sqlite3 $dest
Write-Host "Backup criado: $dest"
```

Após o backup, listar os arquivos existentes:
```powershell
Get-ChildItem db.sqlite3* | Select-Object Name, LastWriteTime, Length | Format-Table
```

Reportar:
- Nome do arquivo de backup criado
- Tamanho do arquivo (confirma que a cópia não está vazia)
- Lista de todos os backups existentes

Para restaurar um backup específico (se algo der errado na migration):
```powershell
Copy-Item db.sqlite3.bak_TIMESTAMP db.sqlite3
```

Nota: Este comando é apenas para desenvolvimento. Em produção (PostgreSQL), usar `pg_dump`.
