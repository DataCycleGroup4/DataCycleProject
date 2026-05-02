$drive  = if ($env:SMB_BOOKING_DRIVE) { $env:SMB_BOOKING_DRIVE } else { "X" }
$bucket = if ($env:GCS_BUCKET)        { $env:GCS_BUCKET }        else { throw "GCS_BUCKET env var is not set" }

Get-ChildItem "${drive}:\*.xls" | ForEach-Object {

	$name = $_.Name
	$month = $null

	if ($name -match "RoomAllocations_\d{4}(\d{2})") {
		$month = $matches[1]
	}

	$dest = "gs://$bucket/raw/bellevuebooking/xls/${month}/"

	Write-Host "Uploading $($_.Name) to destination: $dest"
	try {
		gsutil cp $_.FullName $dest
	} catch {
    		$errorMessage = "Data transfer failed for $($_.Name). Error: $($_.Exception.Message)"
   		gcloud logging write solar-log-errors "$errorMessage" --severity=ERROR
    		Write-Error $errorMessage
	}
}
