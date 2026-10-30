<# User-authorized 20x10 qualification of TOP THREE healthy 40x5 finalists.
   One Docker at a time; same twenty canonical seeds, immutable source bundles.
   Economic ranking: ratio of means at 1979-12-01, not gain_short verdict.
#>
param([Parameter(Mandatory=$true)][ValidateRange(1,3)][int]$Position)
$ErrorActionPreference='Stop'
$Worktree=(git rev-parse --show-toplevel)
if($LASTEXITCODE -ne 0){throw 'Git worktree unavailable'}
$Repo=Split-Path (Split-Path $Worktree -Parent) -Parent
$RankPath=Join-Path $Worktree 'docs/estim31_top3_frozen_20261030.json'
$Rank=Get-Content -Raw -Encoding UTF8 $RankPath|ConvertFrom-Json
if($Rank.locked_40x5_ranking.Count -ne 3){throw 'Freeze exactly three healthy 40x5 finalists before 20x10'}
$Top=@($Rank.locked_40x5_ranking)
$Selected=$Top[$Position-1]
if($Rank.seeds20.Count -ne 20 -or $Selected.source_bundle_sha256.Length -ne 64){throw 'Invalid frozen seed set or source provenance'}
$Suites=@{
  v161='estim31_v161_safe20261030';v161cap='estim31_v161_motorcap20261030'
  v161coeff='estim31_v161_coeff20261030';capcombo='estim31_v161_capcombo20261030'
  rail1970='estim31_v161_rail1970_20261030';v161policy='estim31_v161_policy20261030'
  noupper='estim31_no_upper20261030'
}
$Prefixes=@{
  v161='estim31v161';v161cap='estim31vcap';v161coeff='estim31vcoef'
  capcombo='estim31capco';rail1970='estim31r1970';v161policy='estim31vp'
  noupper='estim31nohi'
}
if(-not $Suites.ContainsKey($Selected.suite)){throw ('Unknown suite '+$Selected.suite)}
$Suite=[string]$Selected.suite
$Name=[string]$Selected.name
$Prefix=$Prefixes[$Suite]
$Bundle=Join-Path $Repo ('results/'+$Suites[$Suite]+'/'+$Name)
$Design=Get-Content -Raw -Encoding UTF8 (Join-Path $Bundle 'design.json')|ConvertFrom-Json
$PriorCampaign=$Prefix+'_'+$Name+'_40x5_20261030'
$Prior=Get-Content -Raw -Encoding UTF8 (Join-Path $Bundle ('results/'+$PriorCampaign+'.json'))|ConvertFrom-Json
if($Prior.source_bundle_sha256 -ne $Selected.source_bundle_sha256 -or $Prior.games.Count -ne 80 -or $Prior.failed_runs.Count -gt 0 -or @($Prior.games|Where-Object{-not $_.game_ok -or $_.game_status -ne 'complete'}).Count -gt 0){throw ('40x5 source/health mismatch '+$Suite+'/'+$Name)}
$Campaign='estim31ten_'+$Prefix+'_'+$Name+'_20x10_20261030'
$Final=Join-Path $Bundle ('results/'+$Campaign+'.json')
if(Test-Path $Final){Write-Output ('EXISTS '+$Campaign);exit 0}
$Active=@(docker ps --format '{{.ID}}')
if($LASTEXITCODE -ne 0 -or $Active.Count -gt 0){throw ('DOCKER_BUSY '+($Active -join ','))}
$Expected='sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659'
$Image=(docker image inspect openttd-lab:latest --format '{{.Id}}')
if($LASTEXITCODE -ne 0 -or $Image.Trim() -ne $Expected){throw 'Docker image changed'}
$C=$Design.configuration
$Vars=@('estim_unifie=31',"eb14_progressive=$($C.eb14)")
if($C.v249_statue -ne 2){$Vars+='v249_statue='+$C.v249_statue}
if($C.eb2_fallback -ne 0){$Vars+='eb2_new_station_fallback='+$C.eb2_fallback}
if($C.air_load_min_pct -ne 0){$Vars+='air_load_min_pct='+$C.air_load_min_pct}
$Vars+='probes=2'
$Variant='OpexAI['+($Vars -join ',')+']'
$PolicyId=$Prefix+'_'+$Name
$Args=@('--campaign',$Campaign,'--reference','OpexAI[probes=2]',
  '--variant',$Variant,'--variant-policy-id',$PolicyId,
  '--primary-metric','profit_year','--decision-rule','gain_short',
  '--min-useful-primary-delta-pct','4','--value-guard-max-loss-pct','100',
  '--required-seeds','20','--required-years','10','--years','10',
  '--start-year','1970','--map-size','8','--max-workers','8',
  '--docker-image-id',$Image,
  '--retain-savegames',('/work/results/'+$Campaign+'_saves'))
Write-Output ('START_TOP3_20x10 position='+$Position+' suite='+$Suite+' name='+$Name+' '+(Get-Date -Format o)+' '+$Variant)
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -e C66_GIT_SHA=99f29d9c858f390de6193978a4f12d3fbdb48127 -e C66_GIT_DIRTY=1 -e C66_DOCKER_IMAGE=openttd-lab:latest -e C66_DOCKER_IMAGE_ID=$Image -v openttd-lab-home:/home/lab -v "${Bundle}:/work" -w /work $Image python3 -B sweeps/bench_1v1_5y_20seeds.py @Args
if($LASTEXITCODE -ne 0){throw ('BENCH_FAILED '+$Campaign)}
Write-Output ('DONE_TOP3_20x10 '+$Campaign+' '+(Get-Date -Format o))
