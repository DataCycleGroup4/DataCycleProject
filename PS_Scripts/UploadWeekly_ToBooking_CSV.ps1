$drive  = if ($env:SMB_BOOKING_DRIVE) { $env:SMB_BOOKING_DRIVE } else { "X" }
$bucket = if ($env:GCS_BUCKET)        { $env:GCS_BUCKET }        else { throw "GCS_BUCKET env var is not set" }

Get-ChildItem "${drive}:\*.csv" | ForEach-Object {
    $name = $_.Name
    $month = if ($name -match "RoomAllocations_\d{4}(\d{2})") { $matches[1] } else { "unknown" }
    $dest = "gs://$bucket/raw/bellevuebooking/csv/${month}/"
    $tempPath = Join-Path $env:TEMP "anon_$name"

    try {
        # Using -Delimiter ";" for Swiss/French CSV standards
        $csvData = Import-Csv -Path $_.FullName -Delimiter ";"

        foreach ($row in $csvData) {
            if ($row."Nom de l'utilisateur") { $row."Nom de l'utilisateur" = "ANONYMIZED" }
            if ($row."Professeur") { $row."Professeur" = "ANONYMIZED" }
        }

        $csvData | Export-Csv -Path $tempPath -NoTypeInformation -Delimiter ";" -Encoding UTF8
        
        Write-Host "Uploading anonymized CSV: $name"
        gsutil cp $tempPath $dest
    } catch {
        $errorMessage = "CSV processing failed for $($_.Name). Error: $($_.Exception.Message)"
        gcloud logging write solar-log-errors "$errorMessage" --severity=ERROR
        Write-Error $errorMessage
    } finally {
        if (Test-Path $tempPath) { Remove-Item $tempPath -Force }
    }
}