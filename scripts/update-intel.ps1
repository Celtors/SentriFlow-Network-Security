<#
  Refresh the bundled tracker lists. MANUAL ONLY: SentriFlow never downloads anything at runtime.
  Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts\update-intel.ps1

  Downloads to a temp file first and only replaces the bundled list after a basic sanity check,
  so a failed or truncated download cannot leave you with an empty blocklist.
  Review the licence lines in THIRD_PARTY_NOTICES.md before committing the refreshed files.
#>
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$target = Join-Path $root "backend\src\sentriflow\data\blocklists"
New-Item -ItemType Directory -Force -Path $target | Out-Null

$lists = @(
    @{ Name = "stevenblack-hosts.txt"; Url = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"; Marker = "0.0.0.0 " },
    @{ Name = "easyprivacy.txt";       Url = "https://easylist.to/easylist/easyprivacy.txt";                   Marker = "||" }
)

foreach ($list in $lists) {
    $tmp = Join-Path ([IO.Path]::GetTempPath()) ("sentriflow-" + $list.Name)
    Write-Host "Downloading $($list.Url)"
    Invoke-WebRequest -Uri $list.Url -OutFile $tmp -UseBasicParsing

    $text = Get-Content -Raw -Path $tmp
    $hits = ([regex]::Matches($text, [regex]::Escape($list.Marker))).Count
    if ((Get-Item $tmp).Length -lt 10000 -or $hits -lt 1000) {
        Remove-Item $tmp -Force
        throw "$($list.Name): download looks wrong (size or content), keeping the existing file."
    }
    Move-Item -Force -Path $tmp -Destination (Join-Path $target $list.Name)
    Write-Host "Updated $($list.Name) ($hits entries)"
}
Write-Host "Done. Restart SentriFlow to load the new lists."
