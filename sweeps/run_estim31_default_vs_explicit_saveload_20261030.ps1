<# Confirm real Save/Load with public defaults AND the explicitly measured
   ESTIM31/EB14/probes values. Never claim numerical trajectory identity:
   OpenTTD runs have known stochastic replay differences. One Docker at a time.
#>
param([Parameter(Mandatory=$true)][string]$Release)
$ErrorActionPreference='Stop'
$Source=(Resolve-Path -LiteralPath $Release).Path
$ManifestFile=Join-Path $Source 'release_manifest.json'
if(-not(Test-Path -LiteralPath $ManifestFile)){throw 'Release manifest absent'}
$Manifest=Get-Content -Raw -Encoding UTF8 -LiteralPath $ManifestFile|ConvertFrom-Json
if(-not $Manifest.deployable_source_ready -or $Manifest.production_ai_updated){
  throw 'Release must be sealed and isolated'
}
if($Manifest.settings_promoted.estim_unifie -ne 31 -or
   $Manifest.settings_promoted.eb14_progressive -ne 3 -or
   $Manifest.settings_promoted.probes -ne 2){throw 'Wrong public-default contract'}
if(-not(Test-Path -LiteralPath (Join-Path $Source 'ai_libraries'))){throw 'NoAI libraries absent'}
$Worktree=git rev-parse --show-toplevel
if($LASTEXITCODE -ne 0){throw 'Missing git worktree'}
$Repo=Split-Path (Split-Path $Worktree -Parent) -Parent
$Output=Join-Path $Repo 'results/estim31_promoted_default_saveload20261030'
if(-not(Test-Path -LiteralPath $Output)){New-Item -ItemType Directory -Path $Output|Out-Null}
$Expected='sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659'
$Image=(docker image inspect openttd-lab:latest --format '{{.Id}}')
if($LASTEXITCODE -ne 0 -or $Image.Trim() -ne $Expected){throw 'Docker image mismatch'}
$Arms=@(
  @{Name='default'; Arm='OpexAI'},
  @{Name='explicit'; Arm='OpexAI[estim_unifie=31,eb14_progressive=3,probes=2]'}
)
foreach($Case in $Arms){
  $Path=Join-Path $Output $Case.Name
  $Result=Join-Path $Path 'saveload_999.json'
  if(Test-Path -LiteralPath $Result){
    $Json=Get-Content -Raw -Encoding UTF8 -LiteralPath $Result|ConvertFrom-Json
    if($Json.status -ne 'OK' -or -not $Json.load_call_proof.positive_ai_marker_exists){
      throw ('Previous Save/Load incomplete: '+$Case.Name)
    }
    Write-Output ('ALREADY_VERIFIED '+$Case.Name)
    continue
  }
  $Busy=@(docker ps --format '{{.ID}}')
  if($LASTEXITCODE -ne 0 -or $Busy.Count -gt 0){throw ('DOCKER_BUSY '+($Busy -join ','))}
  if(-not(Test-Path -LiteralPath $Path)){New-Item -ItemType Directory -Path $Path|Out-Null}
  Write-Output ('START_DEFAULT_PARITY '+$Case.Name+' '+(Get-Date -Format o)+' '+$Case.Arm)
  docker run --rm --cpus=10 --memory=8g --memory-swap=8g `
    --mount "type=bind,source=$Source,target=/work,readonly" `
    --mount "type=bind,source=$Path,target=/diag" `
    -w /work $Image python3 -B sweeps/save_load_roundtrip.py `
    --seed 999 --years-a 1 --years-b 1 --starting-year 1970 `
    --mid-fraction 0.5 --script-debug 4 --arm $Case.Arm `
    --work-dir /diag/work --out /diag/saveload_999.json
  if($LASTEXITCODE -ne 0 -or -not(Test-Path -LiteralPath $Result)){
    throw ('Save/Load runtime failure: '+$Case.Name)
  }
  $Json=Get-Content -Raw -Encoding UTF8 -LiteralPath $Result|ConvertFrom-Json
  if($Json.status -ne 'OK' -or -not $Json.load_call_proof.positive_ai_marker_exists){
    throw ('Save/Load success markers absent: '+$Case.Name)
  }
  Write-Output ('VERIFIED_DEFAULT_PARITY '+$Case.Name+' '+(Get-Date -Format o))
}
Write-Output 'DEFAULT_AND_EXPLICIT_SAVELOAD_OK; numerical replay equality not asserted'
