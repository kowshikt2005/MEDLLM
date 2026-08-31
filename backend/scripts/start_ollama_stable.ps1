param(
    [ValidateSet("cuda_v12", "cpu")]
    [string]$Backend = "cuda_v12",
    [switch]$Persist
)

# Stable defaults for Windows + RTX 40-series with Ollama 0.20.x.
$llmLibrary = $Backend
$flashAttention = "false"
$maxLoadedModels = "1"

if ($Persist) {
    Write-Host "Persisting Ollama environment variables for future terminals..."
    setx OLLAMA_LLM_LIBRARY $llmLibrary | Out-Null
    setx OLLAMA_FLASH_ATTENTION $flashAttention | Out-Null
    setx OLLAMA_MAX_LOADED_MODELS $maxLoadedModels | Out-Null
    Write-Host "Saved: OLLAMA_LLM_LIBRARY=$llmLibrary, OLLAMA_FLASH_ATTENTION=$flashAttention, OLLAMA_MAX_LOADED_MODELS=$maxLoadedModels"
}

Write-Host "Stopping existing Ollama processes..."
Get-Process ollama* -ErrorAction SilentlyContinue | Stop-Process -Force

# Session-level env for this shell/process.
$env:OLLAMA_LLM_LIBRARY = $llmLibrary
$env:OLLAMA_FLASH_ATTENTION = $flashAttention
$env:OLLAMA_MAX_LOADED_MODELS = $maxLoadedModels

Write-Host "Starting Ollama with stable backend settings..."
Write-Host "  OLLAMA_LLM_LIBRARY=$($env:OLLAMA_LLM_LIBRARY)"
Write-Host "  OLLAMA_FLASH_ATTENTION=$($env:OLLAMA_FLASH_ATTENTION)"
Write-Host "  OLLAMA_MAX_LOADED_MODELS=$($env:OLLAMA_MAX_LOADED_MODELS)"
Write-Host ""
Write-Host "Press Ctrl+C to stop Ollama."

ollama serve
