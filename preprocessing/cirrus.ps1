# Define the base folders
$baseFolders = @(
    "G:\cirrus"
)

# Define the centralized output root folder
$outputRoot = "G:\sample_data\cirrus\input"

# Delete the output folder if it exists
if (Test-Path $outputRoot) {
    Remove-Item -Path $outputRoot -Recurse -Force
}

# Create the centralized output folder if it doesn't exist
if (-not (Test-Path $outputRoot)) {
    New-Item -ItemType Directory -Path $outputRoot | Out-Null
}

# Loop through each base folder
foreach ($baseFolder in $baseFolders) {
    # Loop through each subfolder in the current base folder
    Get-ChildItem -Directory $baseFolder | Where-Object { $_.Name -notmatch '_output' } | ForEach-Object {
        $subfolder = $_.FullName

        # Create a matching output folder inside the centralized output root
        $outputFolderName = "$($_.Name)_output"
        $outputFolder = Join-Path $outputRoot $outputFolderName

        # Ensure the output folder exists
        if (-not (Test-Path $outputFolder)) {
            New-Item -ItemType Directory -Path $outputFolder | Out-Null
        }

        # Run the Java command for each subfolder
        & "C:\Users\b2aiUsr\.scripts\zeiss\bin\java.exe" `
            -cp ".;C:\Program Files\MATLAB\MATLAB Runtime\v91\toolbox\javabuilder\jar\javabuilder.jar;C:\Users\b2aiUsr\.scripts\zeiss\cirrusDCMvisualizationsDICOMWrapper20240719_141654\*" `
            demoVis "$subfolder" "$outputFolder" 0
    }
}