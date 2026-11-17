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
# then converts it to the Parquet the API reads (see convert)
download:
	./download.sh $(ARGS)
	$(MAKE) convert ARGS=

# Save each dataset's downloaded CSV/TSV tables as Parquet (fast for the API to read) and
# delete the CSV/TSV. Runs in the API's image, so the host needs no Python packages.
#   make convert                              every dataset
# To redo a dataset, download it again: make download ARGS="<task_id> <dataset_name>"
convert:
	$(DEV) build
	docker run --rm --user $$(id -u):$$(id -g) -v "$(CURDIR)/data:/app/data" ocean-portal-api python convert.py $(ARGS)

attach:
	docker exec -i -t ocean-portal-api /bin/bash

logs:
	docker logs -f ocean-portal-api

.PHONY: server-compose-interactive server-compose server-compose-down download convert attach logs
