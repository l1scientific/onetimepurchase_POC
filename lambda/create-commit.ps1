param($commitMsg, $branchName)

$env:GIT_USER="dylan-l1scientific"
$env:GIT_PASS="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"
git config --global credential.helper "!f() { echo \`"username=`${GIT_USER}`npassword=`${GIT_PASS}\`"; }; f"

Write-Host "# Fetching branches from GitHub Remote" -ForegroundColor black -BackgroundColor white
git fetch github
Write-Host "DONE" -ForegroundColor green

Write-Host "# Pulling any changes from - $branchName -" -ForegroundColor black -BackgroundColor white
git pull github $branchName
Write-Host "DONE" -ForegroundColor green

Write-Host "# Adding all changes" -ForegroundColor black -BackgroundColor white
git add .
Write-Host "DONE" -ForegroundColor green
Write-Host "# Committing changes" -ForegroundColor black -BackgroundColor white
git commit -m $commitMsg
Write-Host "DONE" -ForegroundColor green
Write-Host "# Pushing to master in Alexa Dev Console Remote" -ForegroundColor black -BackgroundColor white
git push -u amazon-developer-remote master
Write-Host "DONE" -ForegroundColor green
Write-Host "# Pushing to - $branchName - in GitHub Remote" -ForegroundColor black -BackgroundColor white
git push -u github master:$branchName
Write-Host "DONE" -ForegroundColor green
Write-Host "Finished all tasks"
