<# Distinct frozen copy; benchmark only. Its ESTIM C121_GE is not proven exact. #>
$ErrorActionPreference='Stop'
$W=(git rev-parse --show-toplevel)
if($LASTEXITCODE -ne 0){throw 'Git unavailable'}
$Repo=Split-Path (Split-Path $W -Parent) -Parent
$Bundle=Join-Path $Repo 'results/estim31_oldge_best_40x5_20261030'
$Meta=Get-Content -Raw -Encoding UTF8 (Join-Path $Bundle 'copy_provenance.json')|ConvertFrom-Json
$Id=$Meta.image_id
$Name='estim31_oldge_best_40x5_20261030'
if(Test-Path (Join-Path $Bundle ('results/'+$Name+'.json'))){Write-Output 'EXISTS';exit 0}
$Busy=@(docker ps --format '{{.ID}}')
if($LASTEXITCODE -ne 0 -or $Busy.Count -gt 0){throw 'DOCKER_BUSY'}
$Actual=(docker image inspect openttd-lab:latest --format '{{.Id}}')
if($LASTEXITCODE -ne 0 -or $Actual.Trim() -ne $Id){throw 'Docker image mismatch'}
Write-Output "START_OLD_GE_40x5 $(Get-Date -Format o)"
docker run --rm --cpus=10 --memory=8g --memory-swap=8g `
  -e C66_GIT_SHA=99f29d9c858f390de6193978a4f12d3fbdb48127 `
  -e C66_GIT_DIRTY=1 -e C66_DOCKER_IMAGE=openttd-lab:latest `
  -e C66_DOCKER_IMAGE_ID=$Id -v openttd-lab-home:/home/lab `
  -v "${Bundle}:/work" -w /work $Id `
  python3 -B sweeps/bench_1v1_5y_20seeds.py `
  --campaign $Name --reference $Meta.options.reference `
  --variant $Meta.options.variant --variant-policy-id $Meta.options.variant_policy_id `
  --decision-rule gain_short --primary-metric profit_year `
  --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 100 `
  --required-seeds 40 --required-years 5 --years 5 --start-year 1970 `
  --map-size 8 --max-workers 8 --docker-image-id $Id `
  --retain-savegames ('/work/results/'+$Name+'_saves')
if($LASTEXITCODE -ne 0){throw 'OLD_GE_40x5_FAILED'}
Write-Output "DONE_OLD_GE_40x5 $(Get-Date -Format o)"
