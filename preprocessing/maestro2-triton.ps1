# $DICOM_OCT_EXPORT_EXE = "G:\OCT_v2\FdaFileParser\exe\DicomOctExport.exe"
$DICOM_OCT_EXPORT_EXE = "C:\Users\sanjay\Downloads\OCT_v2\FdaFileParser\exe\DicomOctExport.exe"
$BaseRoot = "D:\year3+raw\maestro2"
$GlobalOutputRoot = "D:\year3+pre\maestro2"

# Ensure global output root exists
if (-not (Test-Path $GlobalOutputRoot)) {
    New-Item -Path $GlobalOutputRoot -ItemType Directory | Out-Null
}

# Take a snapshot of all input folders at the start, excluding '_output'
$InputFolders = Get-ChildItem -Path $BaseRoot -Recurse -Directory | Where-Object {
    $_.FullName -notmatch '_output$'
}

foreach ($folder in $InputFolders) {
    $InputRoot = $folder.FullName

    # Mirror structure inside GlobalOutputRoot
    $relativePath = $InputRoot.Substring($BaseRoot.Length).TrimStart('\')
    $OutputRoot = Join-Path $GlobalOutputRoot ($relativePath + "_output")

    if (-not (Test-Path $OutputRoot)) {
        New-Item -Path $OutputRoot -ItemType Directory -Force | Out-Null
    }

    Get-ChildItem -Path $InputRoot -Filter *.fda -Recurse | ForEach-Object {
        $inputFile = $_.FullName

        if (Test-Path $inputFile -PathType Leaf) {
            $parentFolder = $_.Directory.Name
            $fileNameNoExt = $_.BaseName

            # Check if path has "UAB"
            if ($_.Directory.FullName -match "UAB") {
                # include grandparent as well
                $grandParentFolder = Split-Path $_.Directory.FullName -Parent | Split-Path -Leaf
                $outputFolderName = "${grandParentFolder}_${parentFolder}_${fileNameNoExt}_fda"
            }
            else {
                $outputFolderName = "${parentFolder}_${fileNameNoExt}_fda"
            }

            $outputFolder = Join-Path $OutputRoot $outputFolderName

            if (-not (Test-Path $outputFolder)) {
                New-Item -Path $outputFolder -ItemType Directory | Out-Null
            }

            # Retry loop (max 3 times)
            $maxRetries = 3
            $retryCount = 0
            $success = $false

            while (-not $success -and $retryCount -lt $maxRetries) {
                $retryCount++

                # Clean folder before retry
                Get-ChildItem -Path $outputFolder -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

                # Run the EXE
                & $DICOM_OCT_EXPORT_EXE $inputFile $outputFolder -octa -enfaceSlabs -segDcm -dcm

                # Wait a bit to ensure files are written
                Start-Sleep -Seconds 2

                # Count files created
                $fileCount = (Get-ChildItem -Path $outputFolder -File | Measure-Object).Count

                if ($fileCount -eq 8 -or $fileCount -eq 3) {
                    $success = $true
                    Write-Host "SUCCESS: $inputFile -> $fileCount files created."
                }
                else {
                    Write-Host "WARNING: $inputFile -> $fileCount files created (attempt $retryCount). Retrying..."
                }
            }

            if (-not $success) {
                Write-Host "FAILED: $inputFile -> Did not reach 8 or 3 files after $maxRetries attempts." -ForegroundColor Red
            }
        }
    }
}