$PRIVATE_DICOM_OCT_EXPORT_EXE = "C:\Users\sanjay\Downloads\OCT_v2\FdaFileParser\exe\DicomOctExport.exe"
$PUBLIC_DICOM_OCT_EXPORT_EXE  = "C:\Users\sanjay\Downloads\DICOMOCTExportTool\DICOMOCTExport.v2.1.2.14\DICOMOCTExport\DicomOctExport.exe"

$BaseRoot = "D:\eyeact\raw\maestro2"

$Versions = @(
    @{ Label = "private"; Exe = $PRIVATE_DICOM_OCT_EXPORT_EXE; OutputRoot = "D:\eyeact\pre\maestro2_private" },
    @{ Label = "public";  Exe = $PUBLIC_DICOM_OCT_EXPORT_EXE;  OutputRoot = "D:\eyeact\pre\maestro2_public" }
)

# Snapshot all input folders once, excluding '_output'
$InputFolders = Get-ChildItem -Path $BaseRoot -Recurse -Directory | Where-Object {
    $_.FullName -notmatch '_output$'
}

foreach ($version in $Versions) {
    $label           = $version.Label
    $exe             = $version.Exe
    $GlobalOutputRoot = $version.OutputRoot

    Write-Host "`n=== Running [$label] version ===" -ForegroundColor Cyan

    if (-not (Test-Path $GlobalOutputRoot)) {
        New-Item -Path $GlobalOutputRoot -ItemType Directory | Out-Null
    }

    foreach ($folder in $InputFolders) {
        $InputRoot = $folder.FullName

        $relativePath = $InputRoot.Substring($BaseRoot.Length).TrimStart('\')
        $OutputRoot   = Join-Path $GlobalOutputRoot ($relativePath + "_output")

        if (-not (Test-Path $OutputRoot)) {
            New-Item -Path $OutputRoot -ItemType Directory -Force | Out-Null
        }

        Get-ChildItem -Path $InputRoot -Filter *.fda -Recurse | ForEach-Object {
            $inputFile = $_.FullName

            if (Test-Path $inputFile -PathType Leaf) {
                $parentFolder  = $_.Directory.Name
                $fileNameNoExt = $_.BaseName

                if ($_.Directory.FullName -match "UAB") {
                    $grandParentFolder = Split-Path $_.Directory.FullName -Parent | Split-Path -Leaf
                    $outputFolderName  = "${grandParentFolder}_${parentFolder}_${fileNameNoExt}_fda"
                }
                else {
                    $outputFolderName = "${parentFolder}_${fileNameNoExt}_fda"
                }

                $outputFolder = Join-Path $OutputRoot $outputFolderName

                if (-not (Test-Path $outputFolder)) {
                    New-Item -Path $outputFolder -ItemType Directory | Out-Null
                }

                $maxRetries = 3
                $retryCount = 0
                $success    = $false

                while (-not $success -and $retryCount -lt $maxRetries) {
                    $retryCount++

                    Get-ChildItem -Path $outputFolder -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

                    & $exe $inputFile $outputFolder -octa -enfaceSlabs -segDcm -dcm

                    Start-Sleep -Seconds 2

                    $fileCount = (Get-ChildItem -Path $outputFolder -File | Measure-Object).Count

                    if ($fileCount -eq 8 -or $fileCount -eq 3) {
                        $success = $true
                        Write-Host "[$label] SUCCESS: $inputFile -> $fileCount files"
                    }
                    else {
                        Write-Host "[$label] WARNING: $inputFile -> $fileCount files (attempt $retryCount). Retrying..."
                    }
                }

                if (-not $success) {
                    Write-Host "[$label] FAILED: $inputFile -> Did not reach 8 or 3 files after $maxRetries attempts." -ForegroundColor Red
                }
            }
        }
    }
}

Write-Host "`nDone. Run compare_outputs.py to compare the two versions:" -ForegroundColor Green
Write-Host "  python compare_outputs.py D:\eyeact\pre\maestro2_private D:\eyeact\pre\maestro2_public" -ForegroundColor Yellow
