git config --global user.email "nobody@nobody.org"
git config --global user.name "Travis CI"

git commit -m "Generated new size report and graph" size.png report.csv
git push "https://${GITHUB_TOKEN}@github.com/britzl/dmengine_size.git" HEAD:master
