<# Frozen ESTIM31 combinatorial exploration against AAAHogEx-115.
   One Docker at a time; no retry or overwrite of existing campaigns.
   Reports rank ratio of Opex and AAA mean profit in the same variant duel,
   NOT the historical gain_short adoption gate or company value. #>
param(
  [Parameter(Mandatory=$true)][string[]]$Names,
  [ValidateRange(1,40)][int]$SeedCount=5,
  [ValidateRange(1,10)][int]$Years=5
)
$ErrorActionPreference='Stop'
$Root=(git rev-parse --show-toplevel)
if($LASTEXITCODE -ne 0){throw 'No Git worktree'}
$DirRoot=Join-Path $Root 'results/estim31_combo2_20261030'
$Expected='sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659'
$Image=(docker image inspect openttd-lab:latest --format '{{.Id}}')
if($LASTEXITCODE -ne 0 -or $Image.Trim() -ne $Expected){throw 'Docker image mismatch'}
$Seeds=@(42,100,7,999,2026)
if($SeedCount -eq 40){
  # Canonical seeds are emitted by the harness when --seeds is omitted.
  $Seeds=@()
} elseif($SeedCount -ne 5){throw 'Use 5 exposure seeds or the 40 canonical seeds'}
foreach($Name in $Names){
  $Dir=Join-Path $DirRoot $Name
  $DesignFile=Join-Path $Dir 'design.json'
  if(-not(Test-Path $DesignFile)){throw "Frozen source missing: $Name"}
  $Design=Get-Content -Raw -Encoding UTF8 $DesignFile | ConvertFrom-Json
  $C=$Design.configuration
  # r3: two setup-only failures (missing adversary and nominal default flag).
  # Keep both partial freezes untouched; a new ID is used for real games.
  $Campaign='estim31combo2_'+$Name+'_'+$SeedCount+'x'+$Years+'_20261030_r3'
  $Out=Join-Path $Dir ('results/'+$Campaign+'.json')
  if(Test-Path $Out){Write-Output "ALREADY_EXISTS $Campaign";continue}
  $Active=@(docker ps --format '{{.ID}}')
  if($LASTEXITCODE -ne 0 -or $Active.Count -gt 0){throw ('DOCKER_BUSY '+($Active -join ','))}
  # ESTIM=31 is already the published default; explicit nominal settings are
  # rejected by C66 when the public value is identical.
  $Settings=@()
  if($C.v284_rail_growth -ne 3){$Settings+="v284_rail_growth=$($C.v284_rail_growth)"}
  if($C.air_load_min_pct -ne 0){$Settings+="air_load_min_pct=$($C.air_load_min_pct)"}
  if($C.v249_statue -ne 2){$Settings+="v249_statue=$($C.v249_statue)"}
  if($C.eb14_progressive -ne 3){$Settings+="eb14_progressive=$($C.eb14_progressive)"}
  $Settings+='probes=2'
  $Variant='OpexAI['+($Settings -join ',')+']'
  $Args=@('--campaign',$Campaign,'--reference','OpexAI[probes=2]',
    '--variant',$Variant,'--variant-policy-id',('combo2_'+$Name),
    '--primary-metric','profit_year','--decision-rule','gain_short',
    '--min-useful-primary-delta-pct','4','--value-guard-max-loss-pct','100',
    '--required-seeds',"$SeedCount",'--required-years',"$Years",'--years',"$Years",
    '--start-year','1970','--map-size','8','--max-workers','8',
    '--docker-image-id',$Image)
  if($Seeds.Count -gt 0){$Args+='--seeds';$Args+=@($Seeds | ForEach-Object {"$_"})}
  Write-Output "START $Campaign variant=$Variant $(Get-Date -Format o)"
  docker run --rm --cpus=10 --memory=8g --memory-swap=8g `
    -e C66_GIT_SHA=10b5197dda97c991f783841b63b1ac19c83cc5b8 `
    -e C66_GIT_DIRTY=1 -e C66_DOCKER_IMAGE=openttd-lab:latest `
    -e C66_DOCKER_IMAGE_ID=$Image `
    -v openttd-lab-home:/home/lab -v "${Dir}:/work" -w /work `
    $Image python3 -B sweeps/bench_1v1_5y_20seeds.py @Args
  if($LASTEXITCODE -ne 0){throw "BENCH_FAILED $Campaign"}
  Write-Output "FINISHED $Campaign $(Get-Date -Format o)"
}
