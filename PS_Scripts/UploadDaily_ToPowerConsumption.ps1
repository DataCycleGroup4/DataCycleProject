Get-ChildItem "Y:\*-Consumption.csv" | ForEach-Object {

	$name = $_.Name
	$month = $null

	if ($name -match "^\d{2}\.(\d{2}).\d{4}") {

		$month = $matches[1] 
	}
	
	$dest = "gs://data-cycle-lake/raw/bellevueconso/powerconsumption/${month}/"
	
	Write-Host "Uploading $($_.Name) to destination: $dest"
	try {
		gsutil cp $_.FullName $dest
	} catch {
    		$errorMessage = "Data transfer failed for $($_.Name). Error: $($_.Exception.Message)"
   		gcloud logging write solar-log-errors "$errorMessage" --severity=ERROR
    		Write-Error $errorMessage
	}
}