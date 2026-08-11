# One-liner: irm https://raw.githubusercontent.com/abhilash333naidu/skills-catalog-governance/main/install.ps1 | iex
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $InstallArguments
)

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/abhilash333naidu/skills-catalog-governance.git"
$TempRoot = $null

try {
    $basePath = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
    $localScript = Join-Path $basePath "scripts/catalog_governance.py"
    if (Test-Path -LiteralPath $localScript -PathType Leaf) {
        $packageRoot = $basePath
    } else {
        $git = Get-Command git -ErrorAction SilentlyContinue
        $TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("skills-catalog-governance-" + [guid]::NewGuid().ToString("N"))
        New-Item -ItemType Directory -Path $TempRoot | Out-Null
        if ($null -ne $git) {
            & $git.Source clone --quiet $RepoUrl (Join-Path $TempRoot "repo")
            if ($LASTEXITCODE -ne 0) {
                throw "could not clone $RepoUrl"
            }
            $packageRoot = Join-Path $TempRoot "repo"
        } else {
            $zipPath = Join-Path $TempRoot "repo.zip"
            $extractRoot = Join-Path $TempRoot "repo"
            Invoke-WebRequest -Uri ($RepoUrl -replace '\.git$', '/archive/refs/heads/main.zip') -OutFile $zipPath
            Expand-Archive -Path $zipPath -DestinationPath $TempRoot
            $extracted = Get-ChildItem -LiteralPath $TempRoot -Directory | Where-Object { $_.Name -ne "repo" } | Select-Object -First 1
            if ($null -eq $extracted) {
                throw "downloaded archive did not contain a repository directory"
            }
            Rename-Item -LiteralPath $extracted.FullName -NewName "repo"
            $packageRoot = $extractRoot
        }
    }

    $scriptPath = Join-Path $packageRoot "scripts/catalog_governance.py"
    # Fail closed on too-old Python instead of letting the tool die with a raw
    # SyntaxError traceback. The tool requires Python 3.10+; let Python itself
    # answer the version comparison (valid syntax on every 3.x).
    $VersionProbe = "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $py) {
        & $py.Source -3 -c $VersionProbe 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $found = (& $py.Source -3 --version 2>&1 | Out-String).Trim()
            throw "Python 3.10 or newer is required to install skills-catalog-governance (found: $found); install it from https://www.python.org/downloads/"
        }
        & $py.Source -3 $scriptPath install @InstallArguments
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    } else {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if ($null -eq $python) {
            throw "Python 3 is required to install skills-catalog-governance"
        }
        & $python.Source -c $VersionProbe 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $found = (& $python.Source --version 2>&1 | Out-String).Trim()
            throw "Python 3.10 or newer is required to install skills-catalog-governance (found: $found); install it from https://www.python.org/downloads/"
        }
        & $python.Source $scriptPath install @InstallArguments
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
} catch {
    Write-Error ("installer failed: " + $_.Exception.Message)
    exit 1
} finally {
    if ($null -ne $TempRoot -and (Test-Path -LiteralPath $TempRoot)) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
