$drive  = if ($env:SMB_BOOKING_DRIVE) { $env:SMB_BOOKING_DRIVE } else { "X" }
$bucket = if ($env:GCS_BUCKET)        { $env:GCS_BUCKET }        else { throw "GCS_BUCKET env var is not set" }

Get-ChildItem "${drive}:\*.xls" | ForEach-Object {
    $name = $_.Name
    $month = if ($name -match "RoomAllocations_\d{4}(\d{2})") { $matches[1] } else { "unknown" }
    $dest = "gs://$bucket/raw/bellevuebooking/xls/${month}/"
    
    # We save as .xlsx because .xls is a legacy binary format 
    # that usually requires Excel drivers to write.
    $tempPath = Join-Path $env:TEMP ($name -replace "\.xls$", ".xlsx")

    try {
        # Import data from legacy XLS
        $data = Import-Excel -Path $_.FullName

        foreach ($row in $data) {
            if ($row."Nom de l'utilisateur") { $row."Nom de l'utilisateur" = "ANONYMIZED" }
            if ($row."Professeur") { $row."Professeur" = "ANONYMIZED" }
        }

        # Export to a modern XLSX file (no Excel needed)
        $data | Export-Excel -Path $tempPath -ShowBreakdown:$false

        Write-Host "Uploading anonymized Excel file: $name"
        gsutil cp $tempPath $dest
    } catch {
        $errorMessage = "XLS processing failed for $($_.Name). Error: $($_.Exception.Message)"
        gcloud logging write solar-log-errors "$errorMessage" --severity=ERROR
        Write-Error $errorMessage
    } finally {
        if (Test-Path $tempPath) { Remove-Item $tempPath -Force }
    }
}