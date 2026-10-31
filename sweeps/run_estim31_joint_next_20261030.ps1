<# ESTIM31 interaction discovery, write-once, no new default. #>
param([string[]]$Names = @())
$ErrorActionPreference = 'Stop'
$Root = (git rev-parse --show-toplevel)
if($LASTEXITCODE -ne 0){ throw 'git root not resolved' }
$Main = Split-Path (Split-Path $Root -Parent) -Parent
$Top = Join-Path $Main 'results/estim31_joint_next20261030'
$Allowed = @('mix_a100_w15_statue0_eb2','mix_a100_w15_statue0_load25',
  'mix_a125_r125_w05_flat_statue0','mix_a125_w15_eb142_load25',
  'mix_a100_r125_w15_eb142_statue0','mix_a125_w15_eb2_load25',
  'mix_a150_w15_statue0_eb2','mix_a075_r125_w15_statue0')
if($Names.Count -eq 0){ $Names = $Allowed }
foreach($Name in $Names){
  if($Name -notin $Allowed){ throw "Unapproved experiment $Name" }
  $Dir = Join-Path $Top $Name
  $DesignFile = Join-Path $Dir 'design.json'
  if(-not(Test-Path $DesignFile)){ throw "Absent design $Name" }
  $Design = Get-Content -Raw -Encoding UTF8 $DesignFile | ConvertFrom-Json
  $Campaign = 'estim31next_'+$Name+'_5x5_20261030'
  $Summary = Join-Path $Dir ('results/'+$Campaign+'.json')
  if(Test-Path $Summary){ Write-Output "EXISTS $Name"; continue }
  $Busy = @(docker ps --format '{{.ID}}')
  if($LASTEXITCODE -ne 0){ throw 'Unable to inspect Docker status' }
  if($Busy.Count -gt 0){ throw ('DOCKER_BUSY '+($Busy -join ',')) }
  $Vars = @("eb14_progressive=$($Design.configuration.eb14)",
    'estim_unifie=31',"v249_statue=$($Design.configuration.v249_statue)",
    "eb2_new_station_fallback=$($Design.configuration.eb2_fallback)",
    "air_load_min_pct=$($Design.configuration.air_load_min_pct)",'probes=2')
  $Variant = 'OpexAI['+($Vars -join ',')+']'
  Write-Output ("START $Name "+(Get-Date -Format o)+" $Variant")
  docker run --rm --cpus=10 --memory=8g --memory-swap=8g `
    -e C66_GIT_SHA=99f29d9c858f390de6193978a4f12d3fbdb48127 `
    -e C66_GIT_DIRTY=1 `
    -e C66_DOCKER_IMAGE=openttd-lab:latest `
    -e C66_DOCKER_IMAGE_ID=sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659 `
    -v openttd-lab-home:/home/lab -v "${Dir}:/work" -w /work `
    openttd-lab:latest python3 sweeps/bench_1v1_5y_20seeds.py `
    --campaign $Campaign --reference 'OpexAI[probes=2]' `
    --variant $Variant --variant-policy-id ('estim31next_'+$Name) `
    --primary-metric profit_year --decision-rule gain_short `
    --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 100 `
    --required-seeds 5 --required-years 5 --years 5 `
    --seeds 42 100 7 999 2026 --max-workers 8
  if($LASTEXITCODE -ne 0){ throw "BENCH_FAILED $Name" }
  Write-Output ("DONE $Name "+(Get-Date -Format o))
}
