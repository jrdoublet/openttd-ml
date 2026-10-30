<# Write-once joint C121 N1/N2 fleet cap x V161 marginal experiments.
   A completed healthy five-seed screen is mandatory before a 40-seed run.
   Source is a frozen private bundle, not shared/master source. #>
param([Parameter(Mandatory=$true)][ValidateSet('mix_a200_r075_w15_slope',
    'mix_a200_r150_w05_flat_load25')][string]$Name,
    [ValidateSet(5,40)][int]$SeedCount=5)
$ErrorActionPreference='Stop'
$Worktree=(git rev-parse --show-toplevel)
if($LASTEXITCODE -ne 0){throw 'Git worktree not found'}
$Repo=Split-Path (Split-Path $Worktree -Parent) -Parent
$Source=Join-Path $Repo ('results/estim31_v161_motorcap20261030/'+$Name)
$Design=Get-Content -Raw -Encoding UTF8 (Join-Path $Source 'design.json')|ConvertFrom-Json
$Prefix='estim31vcap'
$Suffix=if($SeedCount -eq 40){'40x5'}else{'5x5'}
$Campaign=$Prefix+'_'+$Name+'_'+$Suffix+'_20261030'
$Result=Join-Path $Source ('results/'+$Campaign+'.json')
if(Test-Path $Result){Write-Output "EXISTS $Campaign";exit 0}
if($SeedCount -eq 40){
  $Short=Join-Path $Source ('results/'+$Prefix+'_'+$Name+'_5x5_20261030.json')
  if(-not (Test-Path $Short)){throw 'Missing prior 5x5'}
  $Summary=Get-Content -Raw -Encoding UTF8 $Short|ConvertFrom-Json
  if($Summary.failed_runs.Count -gt 0 -or $Summary.games.Count -ne 10 `
      -or @($Summary.games|Where-Object {-not $_.game_ok -or $_.game_status -ne 'complete'}).Count -gt 0){
      throw 'Unhealthy prior 5x5'
  }
}
$Busy=@(docker ps --format '{{.ID}}')
if($LASTEXITCODE -ne 0 -or $Busy.Count -gt 0){throw ('DOCKER_BUSY '+($Busy -join ','))}
$Expected='sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659'
$Image=(docker image inspect openttd-lab:latest --format '{{.Id}}')
if($LASTEXITCODE -ne 0 -or $Image.Trim() -ne $Expected){throw 'Docker image mismatch'}
$C=$Design.configuration
$Vars=@("eb14_progressive=$($C.eb14)",'estim_unifie=31')
if($C.v249_statue -ne 2){$Vars+='v249_statue='+$C.v249_statue}
if($C.eb2_fallback -ne 0){$Vars+='eb2_new_station_fallback='+$C.eb2_fallback}
if($C.air_load_min_pct -ne 0){$Vars+='air_load_min_pct='+$C.air_load_min_pct}
$Vars+='probes=2'
$Variant='OpexAI['+($Vars -join ',')+']'
$Args=@('--campaign',$Campaign,'--reference','OpexAI[probes=2]',
  '--variant',$Variant,'--variant-policy-id',($Prefix+'_'+$Name),
  '--primary-metric','profit_year','--decision-rule','gain_short',
  '--min-useful-primary-delta-pct','4','--value-guard-max-loss-pct','100',
  '--required-seeds',"$SeedCount",'--required-years','5',
  '--years','5','--start-year','1970','--map-size','8',
  '--max-workers','8','--docker-image-id',$Image)
if($SeedCount -eq 5){$Args+=@('--seeds','42','100','7','999','2026')}
if($SeedCount -eq 40){$Args+=@('--retain-savegames',('/work/results/'+$Campaign+'_saves'))}
Write-Output "START $Campaign $(Get-Date -Format o) $Variant"
docker run --rm --cpus=10 --memory=8g --memory-swap=8g `
  -e C66_GIT_SHA=99f29d9c858f390de6193978a4f12d3fbdb48127 `
  -e C66_GIT_DIRTY=1 -e C66_DOCKER_IMAGE=openttd-lab:latest `
  -e C66_DOCKER_IMAGE_ID=$Image `
  -v openttd-lab-home:/home/lab -v "${Source}:/work" -w /work `
  $Image python3 -B sweeps/bench_1v1_5y_20seeds.py @Args
if($LASTEXITCODE -ne 0){throw "BENCH_FAILED $Campaign"}
Write-Output "DONE $Campaign $(Get-Date -Format o)"
