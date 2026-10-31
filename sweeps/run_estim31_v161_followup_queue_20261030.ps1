<# Serial five-seed economic exploration; each child checks Docker exclusivity.
   No existing campaign is replayed; no partial JSONL can be qualification.
   Every candidate carries its own AAA profit denominator. #>
$ErrorActionPreference='Stop'
$Runner='sweeps/run_estim31_v161_motorcap_20261030.ps1'
$Runs=@(
  @{suite='v161cap';name='mix_a200_r075_w15_slope'},
  @{suite='v161policy';name='v161_a200_r075_w15_statue0'},
  @{suite='noupper';name='v161_a200_r075'},
  @{suite='v161policy';name='v161_a200_r075_w15_eb142'},
  @{suite='v161policy';name='v161_a200_r075_w15_load25'},
  @{suite='v161cap';name='mix_a200_r150_w05_flat_load25'},
  @{suite='v161policy';name='v161_a200_r075_w15_statue0_eb142'},
  @{suite='noupper';name='v161_motorcap_a200_r075'}
)
foreach($Run in $Runs){
  $busy=@(docker ps --format '{{.ID}}')
  if($LASTEXITCODE -ne 0 -or $busy.Count -gt 0){
    throw ('DOCKER_BUSY before queued experiment '+$Run.suite+' '+$Run.name)
  }
  Write-Output "FOLLOWUP_START $($Run.suite) $($Run.name) $(Get-Date -Format o)"
  powershell -NoProfile -ExecutionPolicy Bypass -File $Runner -Suite $Run.suite -Name $Run.name -SeedCount 5
  if($LASTEXITCODE -ne 0){throw ('FAILED '+$Run.suite+' '+$Run.name)}
  Write-Output "FOLLOWUP_DONE $($Run.suite) $($Run.name) $(Get-Date -Format o)"
}
Write-Output "FOLLOWUP_QUEUE_COMPLETE $(Get-Date -Format o)"
