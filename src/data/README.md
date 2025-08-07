If any changes come to this subtree, from Brain project.. use:

# 1. Fetch the shared split history branch (used as the split base)
git fetch origin shared-data

# 2. Create a local branch from that shared base
git checkout -b shared-data origin/shared-data

# 3. Split your current repo, reusing shared-data as the base
git subtree split --prefix=src/data --onto=shared-data HEAD -b new-split

# 4. Push the result to the Shared repo (branch: data)
git push git@github.com:ECC-BFMC/Shared.git new-split:data --force

# 5. Cleanup temp branches
git branch -D shared-data new-split

# 6. Go back to main branch
git checkout main