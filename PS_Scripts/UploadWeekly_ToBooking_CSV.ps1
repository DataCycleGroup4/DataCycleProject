Get-ChildItem "X:\*.csv" | ForEach-Object {

	$name = $_.Name
	$month = $null

	if ($name -match "RoomAllocations_\d{4}(\d{2})") {
		$month = $matches[1]
	}


	$dest = "gs://data-cycle-lake/raw/bellevuebooking/csv/${month}/"

	Write-Host "Uploading $($_.Name) to destination: $dest"
	try {
		gsutil cp $_.FullName $dest
	} catch {
    		$errorMessage = "Data transfer failed for $($_.Name). Error: $($_.Exception.Message)"
   		gcloud logging write solar-log-errors "$errorMessage" --severity=ERROR
    		Write-Error $errorMessage
	}
}

	