.PHONY: help fmt sec up reqs conda-run conda-clean docker-run docker-clean

help:
	@printf "Usage: make [target]\n"
	@printf "Targets:\n"
	@printf "\thelp - show this help message\n"
	@printf "\tfmt - run formatter\n"
	@printf "\tsec - run security checks\n"
	@printf "\tup - git pull, add, commit, push\n"
	@printf "\treqs - generate requirements.txt\n"
	@printf "\tconda-run - create conda environment\n"
	@printf "\tconda-clean - remove conda environment\n"
	@printf "\tdocker-run - run docker container\n"
	@printf "\tdocker-clean - remove docker container\n"

fmt:
	# sort and remove unused imports
	pip install isort
	isort .
	pip install autoflake
	autoflake --remove-all-unused-imports --recursive --in-place .

	# format
	pip install ruff
	ruff format --config line-length=500 .

sec:
	pip install bandit
	pip install safety

	bandit -r .
	safety check --full-report

up:
	git pull
	git add .
	git commit -m "up"
	git push

upm:
	git pull
	git add .
	git commit -m "${m}"
	git push

reqs:
	pip install pipreqs
	rm -rf requirements.txt
	pipreqs .

conda-run:
	# to emulate x86_64 run: conda config --env --set subdir osx-64
	# to emulate arm64 run: conda config --env --set subdir osx-arm64
	# check with: conda info

	conda deactivate
	conda config --set auto_activate_base false
	conda activate base

	conda create --yes --name main python=3.11 anaconda
	conda activate main
	pip install -r requirements.txt

	# take snapshot
	conda env export > conda-environment.yml

conda-clean:
	conda deactivate
	conda remove --yes --name main --all
	conda env list

docker-run:
	docker-compose up
	docker ps --all
	docker exec -it main /bin/bash

docker-clean:
	docker-compose down

	# wipe docker
	docker stop $(docker ps -a -q)
	docker rm $(docker ps -a -q)
	docker rmi $(docker images -q)
	yes | docker container prune
	yes | docker image prune
	yes | docker volume prune
	yes | docker network prune
	yes | docker system prune

	# check if successful
	docker ps --all
	docker images
	docker system df
	docker volume ls
	docker network ls
