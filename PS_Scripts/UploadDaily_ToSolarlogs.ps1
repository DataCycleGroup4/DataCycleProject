$drive  = if ($env:SMB_SOLAR_DRIVE) { $env:SMB_SOLAR_DRIVE } else { "Z" }
$bucket = if ($env:GCS_BUCKET)      { $env:GCS_BUCKET }      else { throw "GCS_BUCKET env var is not set" }

Get-ChildItem "${drive}:\*.csv" | ForEach-Object {

	$name = $_.Name
	$month = $null

	if ($name -match "^\d{2}\.(\d{2}).\d{4}") {
	#format 01.02.2023-PV.csv

	$month = $matches[1]
	$dest = "gs://$bucket/raw/solarlogs/productionhistory/${month}/"
	Write-Host "Uploading $($_.Name) to destination: $dest"

	try {
		gsutil cp $_.FullName $dest
	} catch {
    	$errorMessage = "Data transfer failed for $($_.Name). Error: $($_.Exception.Message)"
   		gcloud logging write solar-log-errors "$errorMessage" --severity=ERROR
    	Write-Error $errorMessage
	}

	}

	elseif ($name -match "^min\d{2}(\d{2})\d{2}") {
	#format min230201.csv

	$month = $matches[1]
	$dest = "gs://$bucket/raw/solarlogs/production/${month}/"
	Write-Host "Uploading $($_.Name) to destination: $dest"

	try {
		gsutil cp $_.FullName $dest
	} catch {
    	$errorMessage = "Data transfer failed for $($_.Name). Error: $($_.Exception.Message)"
   		gcloud logging write solar-log-errors "$errorMessage" --severity=ERROR
    	Write-Error $errorMessage
	}
	}

}
