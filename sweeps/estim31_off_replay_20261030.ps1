<# Determinism diagnostic: unchanged source and OFF settings, never 40×5. #>
param([ValidateSet(1,8)][int]$Workers=1)
$ErrorActionPreference='Stop'
$Worktree = (git rev-parse --show-toplevel)
if($LASTEXITCODE -ne 0){throw 'git root not found'}
$Repo = Split-Path (Split-Path $Worktree -Parent) -Parent
$Base = Join-Path $Repo 'results/estim31_joint_dispatch20261029/a150_r100_w05'
$Target = Join-Path $Repo 'results/estim31_off_replay20261030'
if(-not (Test-Path $Target)){
  New-Item -ItemType Directory -Path $Target | Out-Null
  foreach($dir in @('ai','ai_libraries','sweeps')){
    Copy-Item -LiteralPath (Join-Path $Base $dir) -Destination (Join-Path $Target $dir) -Recurse
  }
  foreach($file in @('Dockerfile','requirements.txt','requirements-ml.txt')){
    Copy-Item -LiteralPath (Join-Path $Base $file) -Destination (Join-Path $Target $file)
  }
}
$Campaign='estim31_off_replay_seed999_2026_'+$Workers+'worker_20261030'
$result=Join-Path $Target ('results/'+$Campaign+'.json')
if(Test-Path $result){Write-Output "EXISTS $Campaign"; exit 0}
$Busy=@(docker ps --format '{{.ID}}')
if($LASTEXITCODE -ne 0){throw 'docker ps unavailable'}
if($Busy.Count -gt 0){throw ('DOCKER_BUSY '+($Busy -join ','))}
$ImageId=(docker image inspect openttd-lab:latest --format '{{.Id}}')
if($LASTEXITCODE -ne 0 -or -not $ImageId){throw 'Unable to inspect fixed image'}
if($ImageId.Trim() -ne 'sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659'){
  throw ('Docker image changed: '+$ImageId)
}
$GitStatus = @(git -C $Repo status --porcelain=v1 --untracked-files=all)
if($LASTEXITCODE -ne 0){throw 'Unable to inspect Git working tree'}
$Status64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($GitStatus -join "`n")))
Write-Output "START $Campaign $(Get-Date -Format o)"
docker run --rm --cpus=10 --memory=8g --memory-swap=8g `
  -e C66_GIT_SHA=99f29d9c858f390de6193978a4f12d3fbdb48127 `
  -e C66_GIT_DIRTY=1 `
  -e "C66_GIT_STATUS_B64=$Status64" `
  -e C66_DOCKER_CPUS=10 -e C66_DOCKER_MEMORY=8g -e C66_DOCKER_MEMORY_SWAP=8g `
  -e C66_DOCKER_IMAGE=openttd-lab:latest `
  -e C66_DOCKER_IMAGE_ID=$ImageId `
  -v openttd-lab-home:/home/lab -v "${Target}:/work" -w /work `
  $ImageId python3 -B sweeps/bench_1v1_5y_20seeds.py `
  --campaign $Campaign --policy-id reference --reference 'OpexAI[probes=2]' `
  --years 5 --start-year 1970 --map-size 8 --seeds 999 2026 `
  --repeats 2 --max-workers $Workers `
  --docker-image openttd-lab:latest --docker-image-id $ImageId
if($LASTEXITCODE -ne 0){throw "FAILED $Campaign"}
Write-Output "DONE $Campaign $(Get-Date -Format o)"
