$out = Join-Path $PSScriptRoot 'plato-hand-v5.blend'
$stream = [System.IO.File]::Create($out)
try { Get-ChildItem (Join-Path $PSScriptRoot 'plato-v5-parts/part-*.bin') | Sort-Object Name | ForEach-Object { $data = [IO.File]::ReadAllBytes($_.FullName); $stream.Write($data,0,$data.Length) } } finally { $stream.Dispose() }
Write-Output "Created: $out"
