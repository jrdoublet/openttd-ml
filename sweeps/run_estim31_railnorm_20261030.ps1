<# Economic discovery for distance-normalized RAIL learned level, sequential. #>
param([string[]]$Names = @('railnorm_a125_r125_w15_slope_statue0',
                           'railnorm_a125_r125_w15_slope_eb142_load25'))
$ErrorActionPreference='Stop'
$Root = (git rev-parse --show-toplevel)
if($LASTEXITCODE -ne 0){throw 'git root unresolved'}
$Main = Split-Path (Split-Path $Root -Parent) -Parent
$Base = Join-Path $Main 'results/estim31_railnorm20261030'
$Allowed = @('railnorm_a125_r125_w15_slope_statue0',
             'railnorm_a125_r125_w15_slope_eb142_load25')
foreach($Name in $Names){
  if($Name -notin $Allowed){throw "Unapproved $Name"}
  $Dir=Join-Path $Base $Name
  $Design=Get-Content -Raw -Encoding UTF8 (Join-Path $Dir 'design.json') | ConvertFrom-Json
  $Campaign='estim31rn_'+$Name+'_5x5_20261030'
  if(Test-Path (Join-Path $Dir ('results/'+$Campaign+'.json'))){Write-Output "EXISTS $Name";continue}
  $Busy=@(docker ps --format '{{.ID}}')
  if($LASTEXITCODE -ne 0){throw 'docker ps failed'}
  if($Busy.Count -ne 0){throw ('Docker busy '+($Busy -join ','))}
  $C=$Design.configuration
  $Variant='OpexAI[estim_unifie=31,eb14_progressive='+$C.eb14_progressive+',v249_statue='+$C.v249_statue+',air_load_min_pct='+$C.air_load_min_pct+',probes=2]'
  Write-Output "START $Name $(Get-Date -Format o)"
  docker run --rm --cpus=10 --memory=8g --memory-swap=8g `
    -e C66_GIT_SHA=99f29d9c858f390de6193978a4f12d3fbdb48127 `
    -e C66_GIT_DIRTY=1 -e C66_DOCKER_IMAGE=openttd-lab:latest `
    -e C66_DOCKER_IMAGE_ID=sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659 `
    -v openttd-lab-home:/home/lab -v "${Dir}:/work" -w /work `
    openttd-lab:latest python3 sweeps/bench_1v1_5y_20seeds.py `
    --campaign $Campaign --reference 'OpexAI[probes=2]' `
    --variant $Variant --variant-policy-id ('estim31rn_'+$Name) `
    --primary-metric profit_year --decision-rule gain_short `
    --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 100 `
    --required-seeds 5 --required-years 5 --years 5 --max-workers 8 `
    --seeds 42 100 7 999 2026
  if($LASTEXITCODE -ne 0){throw "Failed $Name"}
  Write-Output "DONE $Name $(Get-Date -Format o)"
}
