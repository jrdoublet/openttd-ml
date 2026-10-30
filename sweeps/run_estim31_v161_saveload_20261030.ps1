<# Real seed999 Save/Load roundtrip for qualified V161 and interaction finalists.
   Source bundle mounted read-only. One Docker, 10 CPU, 8 GiB, no collision.
   Distinct write-once diagnostic output, not a 40x5 economic comparison. #>
param(
  [ValidateSet('v161','v161cap','v161coeff','capcombo')][string]$Suite='v161cap',
  [Parameter(Mandatory=$true)][string]$Name
)
$ErrorActionPreference='Stop'
$Worktree=(git rev-parse --show-toplevel)
if($LASTEXITCODE -ne 0){throw 'Git worktree unavailable'}
$Repo=Split-Path (Split-Path $Worktree -Parent) -Parent
$Folder=@{
  v161='estim31_v161_safe20261030'
  v161cap='estim31_v161_motorcap20261030'
  v161coeff='estim31_v161_coeff20261030'
  capcombo='estim31_v161_capcombo20261030'
}[$Suite]
$Bundle=Join-Path $Repo ('results/'+$Folder+'/'+$Name)
$DesignFile=Join-Path $Bundle 'design.json'
if(-not(Test-Path $DesignFile)){throw ('Unknown immutable source '+$Suite+'/'+$Name)}
$Config=(Get-Content -Raw -Encoding UTF8 $DesignFile|ConvertFrom-Json).configuration
$Output=Join-Path $Repo ('results/estim31_v161_saveload20261030/'+$Suite+'/'+$Name)
if(Test-Path (Join-Path $Output 'saveload_999.json')){Write-Output "EXISTS $Output";exit 0}
$Active=@(docker ps --format '{{.ID}}')
if($LASTEXITCODE -ne 0 -or $Active.Count -gt 0){throw ('DOCKER_BUSY '+($Active -join ','))}
$Expected='sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659'
$Image=(docker image inspect openttd-lab:latest --format '{{.Id}}')
if($LASTEXITCODE -ne 0 -or $Image.Trim() -ne $Expected){throw 'Docker image mismatch'}
if(-not(Test-Path $Output)){New-Item -ItemType Directory -Path $Output -Force|Out-Null}
$Vars=@("estim_unifie=31","eb14_progressive=$($Config.eb14)")
if($Config.v249_statue -ne 2){$Vars+='v249_statue='+$Config.v249_statue}
if($Config.eb2_fallback -ne 0){$Vars+='eb2_new_station_fallback='+$Config.eb2_fallback}
if($Config.air_load_min_pct -ne 0){$Vars+='air_load_min_pct='+$Config.air_load_min_pct}
$Vars+='probes=2'
$Variant='OpexAI['+($Vars -join ',')+']'
Write-Output "START_SAVELOAD $Suite/$Name $(Get-Date -Format o) $Variant"
docker run --rm --cpus=10 --memory=8g --memory-swap=8g `
  --mount "type=bind,source=$Bundle,target=/work,readonly" `
  --mount "type=bind,source=$Output,target=/diag" `
  -w /work $Image python3 -B sweeps/save_load_roundtrip.py `
  --seed 999 --years-a 1 --years-b 1 --starting-year 1970 `
  --mid-fraction 0.5 --script-debug 4 --arm $Variant `
  --work-dir /diag/work --out /diag/saveload_999.json
if($LASTEXITCODE -ne 0){throw ('SaveLoad failed '+$Suite+'/'+$Name)}
Write-Output "DONE_SAVELOAD $Suite/$Name $(Get-Date -Format o)"
