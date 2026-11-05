# Run only after the merged source/tests have been frozen and commit reviewed.
# One openttd-lab container at a time; never stop containers belonging to others.
$ErrorActionPreference = 'Stop'
$worktree = 'C:\Users\jr\vscode\openttd-ml\openttd-ml\.wt_merge_master_20261105'
$mountRoot = 'C:\Users\jr\vscode\openttd-ml\openttd-ml'
Set-Location -LiteralPath $worktree

$running = @(docker ps --format '{{.Names}}|{{.Image}}')
if ($LASTEXITCODE -ne 0) { throw 'Docker daemon unavailable' }
if (@($running | Where-Object { $_ -match 'openttd-lab' }).Count -ne 0) {
    throw 'An openttd-lab benchmark is already running; do not overlap.'
}

$reference = 'OpexAI[mode_rail=1,mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$variant = 'OpexAI[mode_rail=1,mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,rail_loop=0,v257_demand=0]'
$aaRail = @(
    '--aaahogex-setting','disable_veh_roadveh=1',
    '--aaahogex-setting','disable_veh_tram=1',
    '--aaahogex-setting','disable_veh_ship=1',
    '--aaahogex-setting','disable_veh_aircraft=1'
)
$common = @(
    '--reference',$reference,'--variant',$variant,
    '--mount-root',$mountRoot,'--cpus','10','--memory','8g',
    '--max-workers','10','--start-year','1970','--map-size','8',
    '--repeats','1','--primary-metric','profit_year','--probes','6',
    '--script-debug','--line-telemetry',
    '--value-guard-max-loss-pct','100',
    '--decision-rule','gain_short','--min-useful-primary-delta-pct','4',
    '--policy-id','fusion_default','--variant-policy-id','fusion_off'
) + $aaRail

function Invoke-MergeSmoke($name, $years, [int[]]$seeds) {
    $out = "results/$name.json"
    $log = "results/$name.console.txt"
    if ((Test-Path -LiteralPath $out) -or (Test-Path -LiteralPath $log)) {
        throw "Existing smoke artifacts, refusing overwrite: $name"
    }
    $running = @(docker ps --format '{{.Names}}|{{.Image}}')
    if ($LASTEXITCODE -ne 0 -or @($running | Where-Object { $_ -match 'openttd-lab' }).Count) {
        throw 'Docker unavailable or another openttd-lab process is running'
    }
    $args = @('-X','utf8','sweeps/run_c66_reference.py',
        '--campaign',$name,'--years',[string]$years,
        '--required-seeds',[string]$seeds.Count,
        '--required-years',[string]$years,
        '--seeds') + @($seeds | ForEach-Object { [string]$_ }) +
        @('--out',$out) + $common
    "[$(Get-Date -Format o)] START $name" | Tee-Object -FilePath $log
    & python @args *>> $log
    $exit = $LASTEXITCODE
    "[$(Get-Date -Format o)] END $name exit=$exit" | Tee-Object -FilePath $log -Append
    if ($exit -ne 0) { throw "Smoke failed: $name ($exit)" }
}

Invoke-MergeSmoke 'fusion_master_compile_smoke_1x1_20261105' 1 @(17)
Invoke-MergeSmoke 'fusion_master_rail_smoke_4x6_20261105' 6 @(17,512,314,8191)
'MERGE SMOKES FINISHED (inspect run health and NoAI logs separately)'
