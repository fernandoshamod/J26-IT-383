$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$focus=@('dataset/yelp_business_1000.csv','dataset/yelp_reviews_1000.csv','hybrid_simulation_v1/real_vendor_profiles.csv','hybrid_simulation_v1/synthetic_service_options.csv','hybrid_simulation_v1/synthetic_event_requirements.csv','hybrid_simulation_v1/synthetic_availability.csv','hybrid_simulation_v1/synthetic_collaboration_scenarios.csv','vendor_compatibility_matrix.csv','vendor_risk_dataset.csv')
$quality=[System.Collections.Generic.List[object]]::new();$cache=@{}
function AddQ($file,$field,$check,$count,$den,$note){$quality.Add([pscustomobject]@{file=$file;field=$field;check=$check;count=$count;denominator=$den;note=$note})}
foreach($file in $focus){
 $rows=@(Import-Csv (Join-Path $root $file));$cache[$file]=$rows
 $missing=@{};$ids=@{};$fields=@($rows[0].PSObject.Properties.Name);foreach($f in $fields){$missing[$f]=0}
 $key=if($file -match 'reviews_1000'){'review_id'}elseif($file -match 'service_options'){'service_option_id'}elseif($file -match 'event_requirements'){'event_id'}elseif($file -match 'collaboration'){'simulated_collaboration_id'}elseif($file -match 'availability|compatibility'){''}else{'business_id'}
 foreach($row in $rows){
  foreach($prop in $row.PSObject.Properties){if([string]::IsNullOrWhiteSpace([string]$prop.Value)){$missing[$prop.Name]++}}
  if($key){$v=[string]($row.$key);if(!$ids.ContainsKey($v)){$ids[$v]=0};$ids[$v]++}
 }
 foreach($f in $fields){if($missing[$f] -gt 0){AddQ $file $f 'missing_or_blank' $missing[$f] $rows.Count 'Blank or whitespace'}}
 if($key){$d=0;foreach($n in $ids.Values){if($n -gt 1){$d+=$n}};AddQ $file $key 'blank_id_rows' $missing[$key] $rows.Count 'Candidate primary key';AddQ $file $key 'rows_with_duplicate_id' $d $rows.Count 'All rows in duplicate key groups'}
}
$p=$cache['hybrid_simulation_v1/real_vendor_profiles.csv'];$o=$cache['hybrid_simulation_v1/synthetic_service_options.csv'];$e=$cache['hybrid_simulation_v1/synthetic_event_requirements.csv'];$a=$cache['hybrid_simulation_v1/synthetic_availability.csv'];$b=$cache['hybrid_simulation_v1/synthetic_collaboration_scenarios.csv'];$r=$cache['vendor_risk_dataset.csv']
$profileIds=[System.Collections.Generic.HashSet[string]]::new([string[]]@($p.business_id));$optionVendorIds=[System.Collections.Generic.HashSet[string]]::new([string[]]@($o.business_id));$eventIds=[System.Collections.Generic.HashSet[string]]::new([string[]]@($e.event_id))
$checks=@(@('hybrid_simulation_v1/synthetic_service_options.csv','business_id','profile'),@('vendor_risk_dataset.csv','business_id','profile'),@('hybrid_simulation_v1/synthetic_availability.csv','event_id','event'),@('hybrid_simulation_v1/synthetic_availability.csv','business_id','option'),@('hybrid_simulation_v1/synthetic_collaboration_scenarios.csv','event_id','event'),@('hybrid_simulation_v1/synthetic_collaboration_scenarios.csv','vendor_a_id','option'),@('hybrid_simulation_v1/synthetic_collaboration_scenarios.csv','vendor_b_id','option'))
foreach($check in $checks){$file=$check[0];$field=$check[1];$set=switch($check[2]){'profile'{$profileIds};'event'{$eventIds};'option'{$optionVendorIds}};$n=0;foreach($row in $cache[$file]){if(!$set.Contains([string]($row.$field))){$n++}};AddQ $file $field 'unmatched_foreign_key_rows' $n $cache[$file].Count $check[2]}
$services=[System.Collections.Generic.HashSet[string]]::new();$locations=[System.Collections.Generic.HashSet[string]]::new();foreach($row in $o){[void]$services.Add([string]$row.service_category);[void]$locations.Add("$($row.simulated_service_city)|$($row.simulated_service_state)")}
AddQ 'hybrid_simulation_v1/synthetic_service_options.csv' 'service_category' 'distinct_values' $services.Count $o.Count (($services|Sort-Object) -join '; ')
AddQ 'hybrid_simulation_v1/synthetic_service_options.csv' 'simulated_service_city,state' 'distinct_location_pairs' $locations.Count $o.Count 'Simulated areas'
$badPrice=0;foreach($row in $o){$v=0.0;if(-not [double]::TryParse([string]$row.unit_price,[ref]$v) -or $v -le 0 -or [double]::IsNaN($v) -or [double]::IsInfinity($v)){$badPrice++}}
AddQ 'hybrid_simulation_v1/synthetic_service_options.csv' 'unit_price' 'nonpositive_or_nonfinite_price_rows' $badPrice $o.Count 'Synthetic USD unit prices'
$pairs=@($cache['vendor_compatibility_matrix.csv']|ForEach-Object {(@($_.service_1,$_.service_2)|Sort-Object) -join '|'})
$dupPairs=($pairs|Group-Object|Where-Object Count -gt 1|ForEach-Object Count|Measure-Object -Sum).Sum;if(!$dupPairs){$dupPairs=0}
AddQ 'vendor_compatibility_matrix.csv' 'service_1,service_2' 'rows_with_duplicate_unordered_pair' $dupPairs $pairs.Count 'Category pairs'
AddQ 'vendor_compatibility_matrix.csv' 'service_1,service_2' 'distinct_unordered_pairs' @($pairs|Sort-Object -Unique).Count $pairs.Count 'Static heuristic'
AddQ 'hybrid_simulation_v1/synthetic_event_requirements.csv' 'event_type' 'distinct_values' @($e.event_type|Sort-Object -Unique).Count $e.Count (($e.event_type|Sort-Object -Unique) -join '; ')
$akeys=@($a|ForEach-Object {"$($_.event_id)|$($_.business_id)|$($_.event_date)"})
$adup=($akeys|Group-Object|Where-Object Count -gt 1|ForEach-Object Count|Measure-Object -Sum).Sum;if(!$adup){$adup=0}
AddQ 'hybrid_simulation_v1/synthetic_availability.csv' 'event_id,business_id,event_date' 'rows_with_duplicate_composite_key' $adup $a.Count 'Historical sample only'
AddQ 'hybrid_simulation_v1/synthetic_collaboration_scenarios.csv' 'simulated_conflict' 'distinct_values' @($b.simulated_conflict|Sort-Object -Unique).Count $b.Count (($b.simulated_conflict|Sort-Object -Unique) -join '; ')
$quality|Export-Csv (Join-Path $PSScriptRoot 'data_quality_report.csv') -NoTypeInformation -Encoding UTF8
Write-Output "quality_rows=$($quality.Count)"
