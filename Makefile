DEV = docker compose --compatibility -f docker-compose.yml -f docker-compose-dev.yml

# Local: http://localhost:8002/api/datasets (foreground / background)
server-compose-interactive:
	$(DEV) up --build

server-compose:
	$(DEV) up --build -d

server-compose-down:
	$(DEV) down

# Download a GNPS2 task's tables into data/ (runs on the host; the container sees them at once)
#   make download                                  the Ocean FBMN dataset
#   make download ARGS="<task_id> <dataset_name>"  any FBMN or EB task
download:
	./download.sh $(ARGS)

attach:
	docker exec -i -t ocean-portal-api /bin/bash

logs:
	docker logs -f ocean-portal-api

.PHONY: server-compose-interactive server-compose server-compose-down download attach logs
