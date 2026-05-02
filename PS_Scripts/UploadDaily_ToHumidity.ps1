$drive  = if ($env:SMB_CONSO_DRIVE) { $env:SMB_CONSO_DRIVE } else { "Y" }
$bucket = if ($env:GCS_BUCKET)      { $env:GCS_BUCKET }      else { throw "GCS_BUCKET env var is not set" }

Get-ChildItem "${drive}:\*-Humidity.csv" | ForEach-Object {

	$name = $_.Name
	$month = $null

	if ($name -match "^\d{2}\.(\d{2}).\d{4}") {

		$month = $matches[1]
	}

	$dest = "gs://$bucket/raw/bellevueconso/humidity/${month}/"

	Write-Host "Uploading $($_.Name) to destination: $dest"
	try {
		gsutil cp $_.FullName $dest
	} catch {
    		$errorMessage = "Data transfer failed for $($_.Name). Error: $($_.Exception.Message)"
   		gcloud logging write solar-log-errors "$errorMessage" --severity=ERROR
    		Write-Error $errorMessage
	}
}
