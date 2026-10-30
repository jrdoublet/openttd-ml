<# Sequential immutable ESTIM-31 5x5/40x5 experiments. Never launch while any
   Docker container is active; no default changes and no probe=770. #>
param(
    [Parameter(Mandatory=$true)][string]$Repository,
    [string[]]$Names = @(
        'a200_r075_w15_slope', 'a175_r100_w30_slope',
        'a175_r075_w05_slope', 'a100_r150_w05_flat',
        'a125_r150_w30_flat', 'a175_r125_w30_flat',
        'a200_r150_w05_flat_load25', 'a075_r075_w30_slope',
        'a125_r075_w05_slope', 'a100_r150_w15_slope'
    ),
    [ValidateSet(5,40)][int]$SeedCount = 5
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath $Repository).Path
$Folder = Join-Path $Root 'results/estim31_joint_newgrid20261030'
$Seeds = @(42,100,7,999,2026)
if ($SeedCount -eq 40) {
    $Seeds = @(42,100,7,999,2026,1,17,73,314,512,1024,1337,4096,8191,
      12345,54321,65537,123456,424242,8675309,423960,613553,515222,
      781335,375172,999533,442018,746035,455216,230185,706990,
      983759,802204,232037,723002,313707,701256,292001,841478,59527)
}
if ($Seeds.Count -ne $SeedCount) {throw 'Wrong seed count'}
foreach ($Name in $Names) {
    if ($Name -notmatch '^a(075|100|125|175|200)_r(075|100|125|150)_w(05|15|30)_(flat|slope)(_load25)?$') {
        throw "Invalid new combination: $Name"
    }
    $Dir = Join-Path $Folder $Name
    if (-not (Test-Path (Join-Path $Dir 'design.json'))) {throw "Unprepared: $Name"}
    $Campaign = 'grid31_'+$Name+'_'+$SeedCount+'x5_20261030'
    $Output = Join-Path $Dir ('results/'+$Campaign+'.json')
    if (Test-Path $Output) {Write-Output "SKIP_DONE $Name"; continue}
    if (Test-Path (Join-Path $Dir ('results/'+$Campaign+'.jsonl'))) {
        throw "Partial artifacts present (no auto restart): $Name"
    }
    $Busy = @(docker ps --format '{{.Names}}')
    if ($LASTEXITCODE -ne 0) {throw 'Cannot inspect Docker'}
    if ($Busy.Count -gt 0) {throw ('DOCKER_BUSY '+($Busy -join ','))}
    $Variant = 'OpexAI[eb14_progressive=3,estim_unifie=31,probes=2]'
    if ($Name.EndsWith('_load25')) {
        $Variant = 'OpexAI[eb14_progressive=3,estim_unifie=31,air_load_min_pct=25,probes=2]'
    }
    Write-Output ('START '+$Name+' '+(Get-Date -Format o))
    docker run --rm --cpus=10 --memory=8g --memory-swap=8g `
        -e C66_GIT_SHA=99f29d9c858f390de6193978a4f12d3fbdb48127 `
        -e C66_GIT_DIRTY=1 `
        -e C66_DOCKER_IMAGE=openttd-lab:latest `
        -e C66_DOCKER_IMAGE_ID=sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659 `
        -v openttd-lab-home:/home/lab -v "${Dir}:/work" -w /work `
        openttd-lab:latest python3 sweeps/bench_1v1_5y_20seeds.py `
        --campaign $Campaign --reference 'OpexAI[probes=2]' `
        --variant $Variant --variant-policy-id ('grid31_'+$Name) `
        --primary-metric profit_year --decision-rule gain_short `
        --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 100 `
        --required-seeds 40 --required-years 5 `
        --years 5 --seeds $Seeds --max-workers 8
    if ($LASTEXITCODE -ne 0) {throw "FAILED $Name"}
    Write-Output ('DONE '+$Name+' '+(Get-Date -Format o))
}
