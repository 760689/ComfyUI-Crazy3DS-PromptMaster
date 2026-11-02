# One-click publish helper: push this folder to GitHub.
#
# Usage (run inside the repo root):
#   1) provide a token (either way)
#        $env:GITHUB_TOKEN = "ghp_xxxxxxxx"
#        or write it into _token.txt next to this script (already git-ignored)
#   2) push to an existing empty repo:
#        .\publish.ps1 -Repo "https://github.com/<account>/ComfyUI-Crazy3DS-PromptMaster.git"
#      or let the script create the repo first (private by default):
#        .\publish.ps1 -Repo "https://github.com/<account>/ComfyUI-Crazy3DS-PromptMaster.git" -NewRepo
#      add -Public to create a public repo instead.
#
# Params:
#   -Repo     target repo URL (HTTPS)
#   -Branch   branch name, default main
#   -Message  commit message, default "release: v69"
#   -NewRepo  create the repo via GitHub API when it does not exist yet
#   -Public   with -NewRepo: create a public repo (default private)
#
# NOTE: keep every string in this file ASCII. Windows PowerShell 5.1 reads
#       BOM-less .ps1 files as ANSI, which turns non-ASCII text into mojibake
#       before it ever reaches git.

param(
    [Parameter(Mandatory = $true)][string]$Repo,
    [string]$Branch = "main",
    [string]$Message = "release: v69",
    [switch]$NewRepo,
    [switch]$Public
)

$ErrorActionPreference = "Stop"

# Use the bundled MinGit when the machine has no global git (downloaded next to this repo).
$git = "git"
$bundled = Join-Path (Split-Path $PSScriptRoot -Parent) "_tools\mingit\cmd\git.exe"
if (Test-Path $bundled) { $git = $bundled }
Write-Host "git: $git"
& $git --version | Out-Host

$token = $env:GITHUB_TOKEN
if (-not $token -and (Test-Path "$PSScriptRoot\_token.txt")) {
    $token = (Get-Content "$PSScriptRoot\_token.txt" -Raw).Trim()
}
if (-not $token -and -not $NewRepo) {
    Write-Warning "No GITHUB_TOKEN found. Falling back to stored git credentials."
}

if ($Repo -notmatch "github\.com[:/]+([^/]+)/([^/]+?)(\.git)?$") {
    throw "Cannot parse owner/repo from -Repo: $Repo"
}
$owner = $Matches[1]
$name = $Matches[2]

if ($NewRepo) {
    if (-not $token) { throw "-NewRepo requires GITHUB_TOKEN" }
    $body = @{
        name        = $name
        private     = (-not $Public)
        description = "Crazy3DS PromptMaster - ComfyUI portrait prompt node"
    } | ConvertTo-Json
    Write-Host "creating repo $owner/$name ..."
    Invoke-RestMethod -Method Post -Uri "https://api.github.com/user/repos" `
        -Headers @{ Authorization = "token $token"; "User-Agent" = "c3ds-publish" } `
        -Body ([Text.Encoding]::UTF8.GetBytes($body)) `
        -ContentType "application/json; charset=utf-8" | Out-Null
}

if (-not (Test-Path ".git")) {
    & $git init -b $Branch
    & $git config core.autocrlf false
    & $git config core.quotepath false
}
if (-not (& $git config user.email)) {
    & $git config user.name "Crazy3DS"
    & $git config user.email "crazy3ds@users.noreply.github.com"
}

& $git add -A
$staged = (& $git diff --cached --name-only | Measure-Object).Count
if ($staged -gt 0) {
    & $git commit -m $Message
} else {
    Write-Host "nothing to commit"
}

$pushUrl = $Repo
if ($token) { $pushUrl = $Repo -replace "^https://", "https://x-access-token:$token@" }
& $git remote remove origin 2>$null
& $git remote add origin $pushUrl
Write-Host "pushing $owner/$name ($Branch) ..."
& $git push -u origin $Branch
& $git remote set-url origin $Repo   # drop the token from .git/config right after push

& $git tag -f v69
& $git push -f origin v69

Write-Host ""
Write-Host "done: https://github.com/$owner/$name"
Write-Host "next (optional): publish a GitHub Release for tag v69 and attach ComfyUI-Crazy3DS-PromptMaster-v69.zip"
