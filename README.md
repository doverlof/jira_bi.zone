docker-compose down
docker-compose build --no-cache
rm -rf data/
rm -f celerybeat-schedule*
docker-compose up -d
docker-compose logs -f jira-monitor