Set-Location C:\Users\jr\vscode\openttd-ml\openttd-ml\.wt_rail_loop_20261104
$seedsA = @(704041,90670,527503,246300,334757,764858,851627,349832,157793,860934,283207,526388,477981,182802,549603,279648,568537,892958,708863,779084,981717,111530,650715,949304,262417,93494,243831,245796,599565,441474,538579,441936,404553,775374,685743,304636,31429,898010,274763,869032)
$seedsB = @(202945,714470,784679,902164,749629,107890,40643,455360,160569,29374,114463,324204,775093,324874,627451,897560,957425,851094,697815,789380)
$refR = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$onR  = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,rail_loop=1]'
$refM = 'OpexAI[rail_sibling=1,rail_open=1]'
$onM  = 'OpexAI[rail_sibling=1,rail_open=1,rail_loop=1]'
$aaa = @('--aaahogex-setting','disable_veh_roadveh=1','--aaahogex-setting','disable_veh_tram=1','--aaahogex-setting','disable_veh_ship=1','--aaahogex-setting','disable_veh_aircraft=1')
$common = @('--mount-root','C:\Users\jr\vscode\openttd-ml\openttd-ml','--cpus','10','--memory','8g','--max-workers','10','--start-year','1970','--map-size','8','--repeats','1','--primary-metric','profit_year','--probes','6','--script-debug','--line-telemetry','--value-guard-max-loss-pct','100','--policy-id','reference','--variant-policy-id','rail_loop','--min-useful-primary-delta-pct','4')

function Run($name, $ref, $on, $rule, $years, $seeds, $extra) {
  $nseeds = $seeds.Count
  $args2 = @('-X','utf8','sweeps/run_c66_reference.py','--campaign',$name,'--reference',$ref,'--variant',$on,'--decision-rule',$rule,'--required-seeds',"$nseeds",'--required-years',"$years",'--years',"$years",'--seeds') + ($seeds | ForEach-Object { "$_" }) + @('--out',"results/$name.json") + $common + $extra
  "[$(Get-Date -Format s)] START $name"
  & python @args2 *> "results\$name.console.txt"
  "[$(Get-Date -Format s)] END $name exit=$LASTEXITCODE"
}

Run 'rail_loop_gain_short_rail_40x5_20261104' $refR $onR 'gain_short' 5 $seedsA $aaa
Run 'rail_loop_gain_short_multi_40x5_20261104' $refM $onM 'gain_short' 5 $seedsA @()
Run 'rail_loop_non_erosion_rail_20x10_20261104' $refR $onR 'non_erosion' 10 $seedsB $aaa
Run 'rail_loop_non_erosion_multi_20x10_20261104' $refM $onM 'non_erosion' 10 $seedsB @()
"CHAIN DONE"
