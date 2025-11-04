commit_info=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/commits/$COMMIT_SHA")

committer=$(echo "$commit_info" | jq -r '.commit.committer.name')
author=$(echo "$commit_info" | jq -r '.commit.author.name')
files=$(echo "$commit_info" | jq -r '.files[].filename' | paste -sd ', ' -)

message="**New Commit Triggered Cloud Build!**\n- **Committer:** $committer\n- **Author:** $author\n- **Files Changed:** $files\n- **Commit:** https://github.com/$REPO_OWNER/$REPO_NAME/commit/$COMMIT_SHA\n"

curl -H "Content-Type: application/json" -X POST \
  -d "{\"content\": \"$message\"}" \
  $DISCORD_WEBHOOK_URL
