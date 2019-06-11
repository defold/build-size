git config --global user.email "bjorn.ritzl@gmail.com"
git config --global user.name "Travis CI (bjorn.ritzl@gmail.com)"

git commit -m "Generated new size report and graph [skip ci]" size.png size_small.png report.csv releases.json
git push "https://${GITHUB_TOKEN}@github.com/britzl/dmengine_size.git" HEAD:master
