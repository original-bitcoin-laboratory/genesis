<#
capture_binding.ps1 — bind a running node to the exact bitcoin.exe / DLL bytes that executed it.

Run this INSIDE each guest VM (node A and node B), ideally once at run start and once at run end, so the
deposited evidence proves the block/log artifacts came from processes running the historical v0.1.0 binary
(sha256 fbcac071...), not merely that such a binary exists in the archive.

Usage (in the guest, PowerShell):
    .\capture_binding.ps1 -Run 2026-08-..-relayed-spend -Node nodeB -Phase pre
    ... run the experiment ...
    .\capture_binding.ps1 -Run 2026-08-..-relayed-spend -Node nodeB -Phase post

It writes  EXECUTED_BINARY_BINDING_<Node>_<Phase>.json  next to itself. Copy those out to the run's
evidence folder; they get hashed into the deposit. NOT money.
#>
param(
  [Parameter(Mandatory=$true)][string]$Run,
  [Parameter(Mandatory=$true)][string]$Node,
  [ValidateSet('pre','post')][string]$Phase = 'pre',
  # Which binary this run is supposed to be. Defaults to Satoshi's released v0.1.0 (the JAN09
  # oracle). For the Bitcoin chain's own client pass its hash instead, otherwise a correct run
  # reports 'matches oracle: False' and reads like a failure:
  #   -Oracle cfb59606c032faa933d5007e85d36f4cfd02737fc4bc485ec2d8699aeacba5ac   (v0.1.1)
  [string]$Oracle = 'fbcac071d92e26d82ec917214e334bd43850c0691f113bab1d4741c9bdd30d2d'
)
$ErrorActionPreference = 'Stop'
$ORACLE = $Oracle.ToLower()

function Hash256($p) { if (Test-Path $p) { (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLower() } else { $null } }

# locate the running client (v0.1 process is 'bitcoin')
$proc = Get-CimInstance Win32_Process -Filter "Name='bitcoin.exe'" | Select-Object -First 1
if (-not $proc) { Write-Error "no running bitcoin.exe found in this guest"; exit 1 }
$exe = $proc.ExecutablePath
$dir = Split-Path $exe -Parent
# Get-CimInstance already hands back a DateTime; Get-WmiObject hands back a DMTF string.
# Calling ToDateTime() on the former throws "Specified argument was out of the range of valid
# values. Parameter name: dmtfDate" -- accept either so the script works under both cmdlets.
$ct = $proc.CreationDate
if ($ct -is [string]) { $ct = [Management.ManagementDateTimeConverter]::ToDateTime($ct) }
$createUtc = $ct.ToUniversalTime().ToString('o')

$exeHash = Hash256 $exe
$libeay  = Hash256 (Join-Path $dir 'libeay32.dll')
$mingwm  = Hash256 (Join-Path $dir 'mingwm10.dll')

$rec = [ordered]@{
  run                = $Run
  node               = $Node
  phase              = $Phase
  captured_utc       = (Get-Date).ToUniversalTime().ToString('o')
  vm_hostname        = $env:COMPUTERNAME
  binding_method     = 'live-process-image'
  process = [ordered]@{
    pid              = $proc.ProcessId
    executable_path  = $exe
    command_line     = $proc.CommandLine
    create_time      = $createUtc
  }
  sha256 = [ordered]@{
    'bitcoin.exe'    = $exeHash
    'libeay32.dll'   = $libeay
    'mingwm10.dll'   = $mingwm
  }
  bitcoin_exe_matches_oracle = ($exeHash -eq $ORACLE)
  oracle_sha256      = $ORACLE
  data_dir           = (Join-Path $env:APPDATA 'Bitcoin')
}

$outName = "EXECUTED_BINARY_BINDING_${Node}_${Phase}.json"
$rec | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 -Path (Join-Path $PSScriptRoot $outName)
Write-Host "wrote $outName"
Write-Host ("  bitcoin.exe {0}  matches oracle: {1}" -f $exeHash, $rec.bitcoin_exe_matches_oracle)
Write-Host ("  libeay32.dll {0}" -f $(if ($libeay) { $libeay } else { '(absent - statically linked build)' }))
Write-Host ("  mingwm10.dll {0}" -f $(if ($mingwm) { $mingwm } else { '(absent - statically linked build)' }))
Write-Host ("  pid {0}  path {1}" -f $proc.ProcessId, $exe)
