<# Safe ESTIM31 grid: top-level priors, no GE shortcut under ESTIM. One Docker. #>
param([string[]]$Names = @(),
  [ValidateSet('safe','railnorm','motorjoint','v161')][string]$Suite='safe')
$ErrorActionPreference='Stop'
$Root=(git rev-parse --show-toplevel)
if($LASTEXITCODE -ne 0){throw 'Git worktree absent'}
$Repo=Split-Path (Split-Path $Root -Parent) -Parent
$Prefix='estim31safe'
$Base=Join-Path $Repo 'results/estim31_joint_safe20261030'
$Allowed=@('mix_a200_r150_w05_flat_load25','mix_a200_r075_w15_slope',
  'mix_a175_r125_w30_flat',
  'mix_a100_w15_statue0_eb2','mix_a100_w15_statue0_load25',
  'mix_a125_r125_w05_flat_statue0','mix_a125_w15_eb142_load25',
  'mix_a100_r125_w15_eb142_statue0','mix_a125_w15_eb2_load25',
  'mix_a150_w15_statue0_eb2','mix_a075_r125_w15_statue0')
if($Suite -eq 'railnorm'){
  $Prefix='estim31rnsafe'
  $Base=Join-Path $Repo 'results/estim31_railnorm_safe20261030'
  $Allowed=@('mix_a125_r125_w05_flat_statue0','mix_a100_r125_w15_eb142_statue0')
}
if($Suite -eq 'motorjoint'){
  $Prefix='estim31motor'
  $Base=Join-Path $Repo 'results/estim31_motor_joint20261030'
  $Allowed=@('mix_a200_r150_w05_flat_load25','mix_a200_r075_w15_slope',
    'mix_a125_r125_w05_flat_statue0')
}
if($Suite -eq 'v161'){
  $Prefix='estim31v161'
  $Base=Join-Path $Repo 'results/estim31_v161_safe20261030'
  $Allowed=@('mix_a200_r150_w05_flat_load25','mix_a200_r075_w15_slope',
    'mix_a125_r125_w05_flat_statue0')
}
if($Names.Count -eq 0){$Names=$Allowed}
$ExpectedImage='sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659'
foreach($Name in $Names){
  if($Name -notin $Allowed){throw "Unknown design $Name"}
  $Dir=Join-Path $Base $Name
  $Design=Get-Content -Raw -Encoding UTF8 (Join-Path $Dir 'design.json') | ConvertFrom-Json
  $Campaign=$Prefix+'_'+$Name+'_5x5_20261030'
  if(Test-Path (Join-Path $Dir ('results/'+$Campaign+'.json'))){Write-Output "EXISTS $Name";continue}
  $Busy=@(docker ps --format '{{.ID}}')
  if($LASTEXITCODE -ne 0){throw 'Docker unavailable'}
  if($Busy.Count -gt 0){throw ('DOCKER_BUSY '+($Busy -join ','))}
  $ImageId=(docker image inspect openttd-lab:latest --format '{{.Id}}')
  if($LASTEXITCODE -ne 0 -or $ImageId.Trim() -ne $ExpectedImage){throw 'Docker image ID mismatch'}
  $C=$Design.configuration
  $Vars=@("eb14_progressive=$($C.eb14)",'estim_unifie=31')
  # The C66 policy validator rejects nominal interventions equal to defaults.
  # Off baseline: statue=2, eb2=0, load=0, probes=2.
  if($C.v249_statue -ne 2){$Vars+= "v249_statue=$($C.v249_statue)"}
  if($C.eb2_fallback -ne 0){$Vars+= "eb2_new_station_fallback=$($C.eb2_fallback)"}
  if($C.air_load_min_pct -ne 0){$Vars+= "air_load_min_pct=$($C.air_load_min_pct)"}
  $Vars+='probes=2'
  $Variant='OpexAI['+($Vars -join ',')+']'
  Write-Output "START $Name $(Get-Date -Format o) $Variant"
  docker run --rm --cpus=10 --memory=8g --memory-swap=8g `
    -e C66_GIT_SHA=99f29d9c858f390de6193978a4f12d3fbdb48127 `
    -e C66_GIT_DIRTY=1 -e C66_DOCKER_IMAGE=openttd-lab:latest `
    -e C66_DOCKER_IMAGE_ID=$ImageId `
    -v openttd-lab-home:/home/lab -v "${Dir}:/work" -w /work `
    $ImageId python3 -B sweeps/bench_1v1_5y_20seeds.py `
    --campaign $Campaign --reference 'OpexAI[probes=2]' `
    --variant $Variant --variant-policy-id ($Prefix+'_'+$Name) `
    --primary-metric profit_year --decision-rule gain_short `
    --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 100 `
    --required-seeds 5 --required-years 5 --years 5 --start-year 1970 --map-size 8 `
    --seeds 42 100 7 999 2026 --max-workers 8 --docker-image-id $ImageId
  if($LASTEXITCODE -ne 0){throw "BENCH_FAILED $Name"}
  Write-Output "DONE $Name $(Get-Date -Format o)"
}
