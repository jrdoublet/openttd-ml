# Descriptive paired benchmarks: ESTIM-1 bits 1+2+4+8+16, ranked AIR sites,
# three modal regimes, 40 seeds x 5 years, OpexAI against modal-matched AAAHogEx.
# Instrumented runs are diagnostics, NOT uninstrumented adoption gates.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File sweeps/run_estim1_sites_40x5_pc.ps1
#        powershell ... -File ... -Modes air,rail,multi
param(
    [ValidateSet('air', 'rail', 'multi')]
    [string[]]$Modes = @('air', 'rail', 'multi'),
    [string]$Suffix = '20261027',
    [switch]$Smoke
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# 2 signs + 256 decisions + 512 cost + 1024 scheduler + 2048 loop
# + 4096 task spans + 131072 portfolio/funnel + 67108864 V309 idle.
# Spans are inclusive: subtract children before forming an opcode pie.
$probeMask = 67247874
$seeds = @(42,100,7,999,2026,1,17,373684,314,512,1024,1337,4096,8191,
    12345,54321,65537,123456,424242,8675309,423960,613553,515222,
    781335,375172,999533,442018,746035,455216,230185,706990,983759,
    802204,232037,723002,313707,701256,292001,841478,59527)

foreach ($mode in $Modes) {
    $running = @(docker ps -q)
    if ($LASTEXITCODE -ne 0) { throw 'Docker inaccessible' }
    if ($running.Count -gt 0 -and $running[0]) { throw "Docker already busy; will not start $mode" }

    $settings = @('estim_unifie=31', 'air_site_ranked=1', 'air_site_funnel=1')
    $aaa = @()
    switch ($mode) {
        'air' {
            $settings += @('mode_rail=0', 'mode_road=0', 'mode_water=0')
            $aaa = @('--aaahogex-setting','disable_veh_train=1',
                '--aaahogex-setting','disable_veh_roadveh=1',
                '--aaahogex-setting','disable_veh_tram=1',
                '--aaahogex-setting','disable_veh_ship=1')
        }
        'rail' {
            $settings += @('mode_air=0', 'mode_road=0', 'mode_water=0')
            $aaa = @('--aaahogex-setting','disable_veh_aircraft=1',
                '--aaahogex-setting','disable_veh_roadveh=1',
                '--aaahogex-setting','disable_veh_tram=1',
                '--aaahogex-setting','disable_veh_ship=1')
        }
        'multi' { }
    }

    $campaign = "estim1_sites_diag_${mode}_40x5_${Suffix}"
    $years = 5
    $runSeeds = $seeds
    if ($Smoke) {
        $campaign = "estim1_sites_diag_${mode}_smoke_${Suffix}"
        $years = 1
        $runSeeds = @(42)
    }
    if (Test-Path "results/$campaign.json") { throw "Campaign already exists: $campaign" }
    if (Test-Path "results/$campaign.manifest.json") { throw "Campaign manifest already exists: $campaign" }

    $argsList = @('-X','utf8','sweeps/run_c66_reference.py',
        '--campaign',$campaign,'--policy-id',"estim1_sites_$mode",
        '--reference',('OpexAI[' + ($settings -join ',') + ']'),
        '--start-year','1970','--map-size','8','--years',"$years",'--repeats','1',
        '--seeds') + @($runSeeds | ForEach-Object { "$_" }) + @(
        '--line-telemetry','--line-telemetry-monthly','--station-supply-telemetry',
        '--script-debug','--probes',"$probeMask",'--cpus','9','--memory','8g',
        '--max-workers','9','--network','host') + $aaa
    Write-Host "=== $campaign : $mode / ${years}y / $($runSeeds.Count) seeds / probes=$probeMask ==="
    & python @argsList
    if ($LASTEXITCODE -ne 0) { throw "Campaign failed: $campaign (exit $LASTEXITCODE)" }
}
