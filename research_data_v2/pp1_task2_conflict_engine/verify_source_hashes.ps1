$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$inventory=Import-Csv (Join-Path $root 'research_data_v2/audit_2026-10-17_01/dataset_inventory.csv')
$mismatches=@()
foreach($item in $inventory){
 $path=Join-Path $root $item.path
 $actual=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
 if($actual -ne $item.sha256){$mismatches+=@{path=$item.path;expected=$item.sha256;actual=$actual}}
}
$result=@{checked_at_utc=[DateTime]::UtcNow.ToString('o');inventory_path='research_data_v2/audit_2026-10-17_01/dataset_inventory.csv';file_count=$inventory.Count;mismatch_count=$mismatches.Count;mismatches=$mismatches;scope='Task 1 inventoried datasets, model artifacts and research outputs; production source files were not in that inventory'}
$target=Join-Path $PSScriptRoot 'source_hash_verification.json'
if(Test-Path -LiteralPath $target){throw 'Result already exists; preserving it'}
[System.IO.File]::WriteAllText($target,($result|ConvertTo-Json -Depth 5),[System.Text.UTF8Encoding]::new($false))
Write-Output "checked=$($inventory.Count) mismatches=$($mismatches.Count)"
