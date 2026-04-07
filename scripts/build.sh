sudo docker compose -f docker/docker-compose.prod.yaml down
git pull
sudo docker compose -f docker/docker-compose.prod.yaml up -d