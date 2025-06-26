# 设置环境变量
$env:SUPABASE_URL="https://xehoqrboglykebqvovgj.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhlaG9xcmJvZ2x5a2VicXZvdmdqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTY1OTY5MywiZXhwIjoyMDY1MjM1NjkzfQ.cLsaAsi4aKMJ92OLtFxsuSg4WXkdtPjKZ8D8ib8Wyu8"
$env:FLASK_SECRET_KEY="sibao-studio-secret-key-2024-production"

# 显示启动信息
Write-Host "正在启动 Sibao Studio Web 应用..." -ForegroundColor Green
Write-Host "应用将在 http://localhost:5000 启动" -ForegroundColor Yellow

# 激活虚拟环境 (可选，如果您的 PowerShell 会话已经激活了虚拟环境则不需要)
# .\venv\Scripts\activate

# 启动应用
python app.py 