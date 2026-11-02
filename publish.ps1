# 一键发布脚本：把当前目录推送到 GitHub
#
# 用法（在仓库根目录执行）：
#   1) 先设置令牌（二选一）
#        $env:GITHUB_TOKEN = "ghp_xxxxxxxx"        # 或者写到本目录的 _token.txt（已被 .gitignore 忽略）
#   2) 仓库已在网页建好：
#        .\publish.ps1 -Repo "https://github.com/<你的账号>/ComfyUI-Crazy3DS-PromptMaster.git"
#      仓库还没建（脚本会自动建一个 Private 仓库）：
#        .\publish.ps1 -Repo "https://github.com/<你的账号>/ComfyUI-Crazy3DS-PromptMaster.git" -NewRepo
#      想公开就再加 -Public
#
# 参数：
#   -Repo      目标仓库地址（HTTPS）
#   -Branch    分支名，默认 main
#   -Message   提交信息，默认 "release: v69"
#   -NewRepo   远端不存在时用 GitHub API 自动创建
#   -Public    配合 -NewRepo，创建公开仓库（默认 Private）

param(
    [Parameter(Mandatory = $true)][string]$Repo,
    [string]$Branch = "main",
    [string]$Message = "release: v69",
    [switch]$NewRepo,
    [switch]$Public
)

$ErrorActionPreference = "Stop"

# ---- 解析 git（优先用随包下载的 MinGit，本机没有全局 git）----
$git = "git"
$bundled = Join-Path (Split-Path $PSScriptRoot -Parent) "_tools\mingit\cmd\git.exe"
if (Test-Path $bundled) { $git = $bundled }
Write-Host "使用 git: $git"
& $git --version | Out-Host

# ---- 解析令牌 ----
$token = $env:GITHUB_TOKEN
if (-not $token -and (Test-Path "$PSScriptRoot\_token.txt")) {
    $token = (Get-Content "$PSScriptRoot\_token.txt" -Raw).Trim()
}
if (-not $token -and -not $NewRepo) {
    Write-Warning "未检测到 GITHUB_TOKEN：将尝试用系统已保存的凭据推送（可能被要求输入账号密码）。"
}

# ---- 解析 账号/仓库名 ----
if ($Repo -notmatch "github\.com[:/]+([^/]+)/([^/]+?)(\.git)?$") {
    throw "无法从 -Repo 解析出 账号/仓库名：$Repo"
}
$owner = $Matches[1]
$name = $Matches[2]

# ---- 可选：自动创建仓库 ----
if ($NewRepo) {
    if (-not $token) { throw "-NewRepo 需要 GITHUB_TOKEN" }
    $body = @{
        name        = $name
        private     = (-not $Public)
        description = "Crazy3DS 美女提示词大师 — ComfyUI 商业人像级提示词节点"
    } | ConvertTo-Json
    Write-Host "创建仓库 $owner/$name ..."
    Invoke-RestMethod -Method Post -Uri "https://api.github.com/user/repos" `
        -Headers @{ Authorization = "token $token"; "User-Agent" = "c3ds-publish" } `
        -Body $body -ContentType "application/json" | Out-Null
}

# ---- 初始化 / 提交 ----
if (-not (Test-Path ".git")) {
    & $git init -b $Branch
    & $git config core.autocrlf false
    & $git config core.quotepath false
}
$hasUser = (& $git config user.email)
if (-not $hasUser) {
    & $git config user.name "Crazy3DS"
    & $git config user.email "crazy3ds@users.noreply.github.com"
}
& $git add -A
$staged = (& $git diff --cached --name-only | Measure-Object).Count
if ($staged -gt 0) {
    & $git commit -m $Message
} else {
    Write-Host "没有需要提交的改动。"
}

# ---- 远端与推送 ----
$pushUrl = $Repo
if ($token) {
    $pushUrl = $Repo -replace "^https://", "https://x-access-token:$token@"
}
& $git remote remove origin 2>$null
& $git remote add origin $pushUrl
Write-Host "推送 $owner/$name ($Branch) ..."
& $git push -u origin $Branch
& $git remote set-url origin $Repo   # 推完立刻移除 URL 里的令牌

# ---- 打标签（v69）----
& $git tag -f v69
& $git push -f origin v69

Write-Host ""
Write-Host "完成：https://github.com/$owner/$name"
Write-Host "下一步（可选）：在 GitHub Releases 页面用 v69 标签发布，附件可上传 ComfyUI-Crazy3DS-PromptMaster-v69.zip"
