python check_size.py

git config --global user.email "nobody@nobody.org"
git config --global user.name "Travis CI"

echo ${GITHUB_TOKEN}
git commit -m "Generated new size report and graph" size.png report.csv
git push "https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git"
