<# 40 paired seeds x five years, after completed healthy 5x5; one Docker.
   Economic ordering is external: ignore descriptive gain_short verdicts. #>
param([string[]]$Names = @('mix_a200_r150_w05_flat_load25',
                           'mix_a200_r075_w15_slope'),
  [ValidateSet('safe','railnorm','motorjoint','v161')][string]$Suite='safe')
$ErrorActionPreference='Stop'
$Worktree=(git rev-parse --show-toplevel)
if($LASTEXITCODE -ne 0){throw 'Git root unavailable'}
$Repo=Split-Path (Split-Path $Worktree -Parent) -Parent
$Prefix='estim31safe'
$DirBase=Join-Path $Repo 'results/estim31_joint_safe20261030'
$Allowed=@('mix_a200_r150_w05_flat_load25','mix_a200_r075_w15_slope',
           'mix_a175_r125_w30_flat','mix_a100_w15_statue0_eb2',
           'mix_a100_w15_statue0_load25','mix_a125_r125_w05_flat_statue0',
           'mix_a125_w15_eb142_load25','mix_a100_r125_w15_eb142_statue0',
           'mix_a125_w15_eb2_load25','mix_a150_w15_statue0_eb2',
           'mix_a075_r125_w15_statue0')
if($Suite -eq 'railnorm'){
  $Prefix='estim31rnsafe'
  $DirBase=Join-Path $Repo 'results/estim31_railnorm_safe20261030'
  $Allowed=@('mix_a125_r125_w05_flat_statue0','mix_a100_r125_w15_eb142_statue0')
}
if($Suite -eq 'motorjoint'){
  $Prefix='estim31motor'
  $DirBase=Join-Path $Repo 'results/estim31_motor_joint20261030'
  $Allowed=@('mix_a200_r150_w05_flat_load25','mix_a200_r075_w15_slope',
    'mix_a125_r125_w05_flat_statue0')
}
if($Suite -eq 'v161'){
  $Prefix='estim31v161'
  $DirBase=Join-Path $Repo 'results/estim31_v161_safe20261030'
  $Allowed=@('mix_a200_r150_w05_flat_load25','mix_a200_r075_w15_slope',
    'mix_a125_r125_w05_flat_statue0')
}
$FixedId='sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659'
foreach($Name in $Names){
  if($Name -notin $Allowed){throw ('Not in suite: '+$Name)}
  $Source=Join-Path $DirBase $Name
  $C=(Get-Content -Raw -Encoding UTF8 (Join-Path $Source 'design.json')|ConvertFrom-Json).configuration
  $Screen=$Prefix+'_'+$Name+'_5x5_20261030'
  $ShortFile=Join-Path $Source ('results/'+$Screen+'.json')
  if(-not (Test-Path $ShortFile)){throw ('Missing 5x5 screen: '+$Name)}
  $Short=Get-Content -Raw $ShortFile | ConvertFrom-Json
  if($Short.failed_runs.Count -gt 0 -or $Short.games.Count -ne 10 `
      -or @($Short.games|Where-Object { -not $_.game_ok -or $_.game_status -ne 'complete' }).Count -gt 0){
    throw ('Unhealthy 5x5 screen: '+$Name)
  }
  $Campaign=$Prefix+'_'+$Name+'_40x5_20261030'
  $Archive='/work/results/'+$Campaign+'_saves'
  if(Test-Path (Join-Path $Source ('results/'+$Campaign+'.json'))){Write-Output "EXISTS $Name";continue}
  $Busy=@(docker ps --format '{{.ID}}')
  if($LASTEXITCODE -ne 0){throw 'Docker unavailable'}
  if($Busy.Count -gt 0){throw ('DOCKER_BUSY '+($Busy -join ','))}
  $Image=(docker image inspect openttd-lab:latest --format '{{.Id}}')
  if($LASTEXITCODE -ne 0 -or $Image.Trim() -ne $FixedId){throw 'Image identity mismatch'}
  $Vars=@("eb14_progressive=$($C.eb14)",'estim_unifie=31')
  # Only non-default options may be declared as explicit intervention.
  if($C.v249_statue -ne 2){$Vars+= "v249_statue=$($C.v249_statue)"}
  if($C.eb2_fallback -ne 0){$Vars+= "eb2_new_station_fallback=$($C.eb2_fallback)"}
  if($C.air_load_min_pct -ne 0){$Vars+= "air_load_min_pct=$($C.air_load_min_pct)"}
  $Vars+='probes=2'
  $Variant='OpexAI['+($Vars -join ',')+']'
  Write-Output "START_40x5 $Name $(Get-Date -Format o) $Variant"
  docker run --rm --cpus=10 --memory=8g --memory-swap=8g `
    -e C66_GIT_SHA=99f29d9c858f390de6193978a4f12d3fbdb48127 `
    -e C66_GIT_DIRTY=1 -e C66_DOCKER_IMAGE=openttd-lab:latest `
    -e C66_DOCKER_IMAGE_ID=$Image `
    -v openttd-lab-home:/home/lab -v "${Source}:/work" -w /work `
    $Image python3 -B sweeps/bench_1v1_5y_20seeds.py `
    --campaign $Campaign --reference 'OpexAI[probes=2]' `
    --variant $Variant --variant-policy-id ($Prefix+'_'+$Name) `
    --decision-rule gain_short --primary-metric profit_year `
    --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 100 `
    --required-seeds 40 --required-years 5 --years 5 `
    --start-year 1970 --map-size 8 --max-workers 8 --docker-image-id $Image `
    --retain-savegames $Archive
  if($LASTEXITCODE -ne 0){throw "FAILED_40x5 $Name"}
  Write-Output "DONE_40x5 $Name $(Get-Date -Format o)"
}
