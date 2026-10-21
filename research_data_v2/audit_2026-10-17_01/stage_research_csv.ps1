param(
 [Parameter(Mandatory=$true)][ValidateSet('vendors','vendor_service_options','vendor_availability','vendor_resource_requirements','vendor_pair_evidence','event_scenarios','conflict_test_cases','data_provenance')][string]$Entity,
 [Parameter(Mandatory=$true)][string]$InputCsv
)
$ErrorActionPreference='Stop'
$source=(Resolve-Path -LiteralPath $InputCsv).Path
$schema=Join-Path $PSScriptRoot "schemas/$Entity.csv"
$expected=Get-Content -LiteralPath $schema -TotalCount 1
$actual=Get-Content -LiteralPath $source -TotalCount 1
if($actual -ne $expected){throw "Header mismatch for $Entity; see $schema"}
$rows=@(Import-Csv -LiteralPath $source)
if($rows.Count -eq 0){throw 'No data rows; template files are not observations'}
$definitions=Get-Content (Join-Path $PSScriptRoot 'schema_definitions.json') -Raw | ConvertFrom-Json
$key=$definitions.entities.$Entity.key
$seen=[System.Collections.Generic.HashSet[string]]::new()
$allowed=[System.Collections.Generic.HashSet[string]]::new([string[]]@('REAL_PUBLIC','DERIVED','SYNTHETIC_TEST','UNKNOWN'))
foreach($row in $rows){
 $id=[string]($row.$key)
 if([string]::IsNullOrWhiteSpace($id) -or !$seen.Add($id)){throw "Blank or duplicate ${key}: $id"}
 if(!$allowed.Contains([string]$row.evidence_class)){throw "Invalid evidence_class for $id"}
 if($row.evidence_class -eq 'REAL_PUBLIC'){
  if([string]::IsNullOrWhiteSpace([string]$row.source_uri) -or [string]::IsNullOrWhiteSpace([string]$row.license_or_permission) -or $row.license_or_permission -eq 'UNKNOWN'){throw "Unproven public lineage/permission for $id"}
 }
}
$stage=Join-Path $PSScriptRoot 'staged_imports'
if(!(Test-Path -LiteralPath $stage)){New-Item -ItemType Directory -Path $stage | Out-Null}
$hash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
$dest=Join-Path $stage "$Entity-$($hash.Substring(0,12)).csv"
if(Test-Path -LiteralPath $dest){throw "Stage already exists; preserving it: $dest"}
Copy-Item -LiteralPath $source -Destination $dest
[pscustomobject]@{entity=$Entity;rows=$rows.Count;source_sha256=$hash;staged_file=$dest;validation='header,key,evidence_class,public_source_uri,license'} | ConvertTo-Json | Set-Content -LiteralPath "$dest.manifest.json" -Encoding UTF8
Write-Output "Staged $($rows.Count) rows in $dest"
