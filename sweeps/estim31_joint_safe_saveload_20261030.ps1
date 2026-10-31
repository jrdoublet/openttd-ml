<# Real save/load smoke seed999 on safe ESTIM-31 AIR+RAIL; no AAA competitor.
   Isolated source readonly, separate output; never re-run an existing output. #>
param([string]$Name='mix_a200_r150_w05_flat_load25')
$ErrorActionPreference='Stop'
$Root=(git rev-parse --show-toplevel)
if($LASTEXITCODE -ne 0){throw 'Git worktree unavailable'}
$Repo=Split-Path (Split-Path $Root -Parent) -Parent
$Bundle=Join-Path $Repo ('results/estim31_joint_safe20261030/'+$Name)
$DesignFile=Join-Path $Bundle 'design.json'
if(-not(Test-Path $DesignFile)){throw ('Unknown source '+$Name)}
$C=(Get-Content -Raw -Encoding UTF8 $DesignFile|ConvertFrom-Json).configuration
$Output=Join-Path $Repo ('results/estim31_safe_saveload20261030/'+$Name)
if(Test-Path (Join-Path $Output 'saveload_999.json')){Write-Output "EXISTS $Output";exit 0}
$Busy=@(docker ps --format '{{.ID}}')
if($LASTEXITCODE -ne 0 -or $Busy.Count -gt 0){throw 'Docker busy or unavailable'}
$Image=(docker image inspect openttd-lab:latest --format '{{.Id}}')
$Expected='sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659'
if($LASTEXITCODE -ne 0 -or $Image.Trim() -ne $Expected){throw 'Docker image changed'}
if(-not(Test-Path $Output)){New-Item -ItemType Directory -Path $Output -Force|Out-Null}
$Variant="OpexAI[estim_unifie=31,eb14_progressive=$($C.eb14),v249_statue=$($C.v249_statue),eb2_new_station_fallback=$($C.eb2_fallback),air_load_min_pct=$($C.air_load_min_pct),probes=2]"
Write-Output "START_SAVELOAD $Name $(Get-Date -Format o) $Variant"
docker run --rm --cpus=10 --memory=8g --memory-swap=8g `
  --mount "type=bind,source=$Bundle,target=/work,readonly" `
  --mount "type=bind,source=$Output,target=/diag" `
  -w /work $Image python3 -B sweeps/save_load_roundtrip.py `
  --seed 999 --years-a 1 --years-b 1 --starting-year 1970 `
  --mid-fraction 0.5 --script-debug 4 --arm $Variant `
  --work-dir /diag/work --out /diag/saveload_999.json
if($LASTEXITCODE -ne 0){throw ('SaveLoad failed '+$Name)}
Write-Output "DONE_SAVELOAD $Name $(Get-Date -Format o)"
