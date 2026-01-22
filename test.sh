sudo docker-compose -f docker-compose.dev.yaml down --volumes --remove-orphans
git pull
sudo docker-compose -f docker-compose.dev.yaml up -d
