#git clone http://github.com/catalin-rusnac/replifactory_v7; cd replifactory_v7; make install

default: install run

UI_SERVICE_NAME = ReplifactoryUI

ifeq ($(OS),Windows_NT)
	DEFAULT_TASKS = windows-install
	VENV_NAME ?= .venv
	PYTHON = "flask_app/$(VENV_NAME)/Scripts/python"
install: install_win_dependencies venv
	cd vue && npm install -y
	flask_app/$(VENV_NAME)/Scripts/python -m pip install -r flask_app/requirements.txt
run: windows-service-compile run-flask run-express
else
	DEFAULT_TASKS = install
	PYTHON = python
install: swap install_apt_dependencies node-pi pip ngrok updatepath
	cd vue && npm install -y;
	cd flask_app && pip install -r requirements.txt;
	make services-ctl
run: run-flask run-express
endif

windows-service-compile: kill-flask
	cd flask_app && "$(VENV_NAME)/Scripts/pyinstaller" --noconfirm win32_service.spec

run-flask:
ifeq ($(OS),Windows_NT)
	powershell.exe Start-Process -FilePath "flask_app/dist/win32_service/win32_service.exe" -Verb RunAs install
	powershell.exe Start-Process -FilePath "flask_app/dist/win32_service/win32_service.exe" -Verb RunAs start
else
	$(PYTHON) flask_app/server.py &
endif

run-express:
ifeq ($(OS),Windows_NT)
	qckwinsvc --name $(UI_SERVICE_NAME) --description "Replifactory UI" --script vue/src/server/express_server.js --startImmediately
else
	node vue/src/server/express_server.js &
endif

run-vue:
	cd vue && npm run serve

build:
	cd vue && npm run build

ngrok:
	@echo "Checking for ngrok..."
	@if ! command -v ngrok > /dev/null; then \
		echo "Installing ngrok..."; \
		curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null; \
		echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list; \
		sudo apt-get update; \
		sudo apt install ngrok; \
		echo "ngrok installed."; \
	else \
		echo "ngrok already installed. No changes made."; \
	fi

swap:
	@if ! grep -q 'CONF_SWAPSIZE=1024' /etc/dphys-swapfile; then \
		echo "Increasing swap size..."; \
		sudo dphys-swapfile swapoff; \
		sudo sed -i 's/CONF_SWAPSIZE=[0-9]*/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile; \
		sudo dphys-swapfile setup; \
		sudo dphys-swapfile swapon; \
		echo "Reboot required to increase swap. Please reboot your Raspberry Pi."; \
	else \
		echo "Swap size already 1024. No changes made."; \
	fi


node-pi:
	@if ! command -v node > /dev/null; then \
		echo "Installing Node.js and npm for Raspberry Pi..."; \
		curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -; \
		sudo apt-get install -y nodejs; \
		echo "Node.js and npm installed successfully"; \
	else \
		echo "Node.js and npm already installed. No changes made."; \
	fi

pip:
	@echo "Checking for pip..."
	@if ! command -v pip > /dev/null; then \
  		echo "Installing distutils..."; \
	    sudo apt-get install python3-distutils -y; \
		echo "Installing pip..."; \
		curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py; \
		sudo python3 get-pip.py; \
		rm get-pip.py; \
	fi

copy_to_www:
	@echo "Copying contents of vue/dist/ to /var/www/html..."
	@sudo cp -r vue/dist/* /var/www/html
	@echo "Copied contents of vue/dist/ to /var/www/html."

APT_DEPENDENCIES = python3-distutils python3-scipy python3-numpy libatlas-base-dev python3-dev gfortran libopenblas-dev

install_apt_dependencies: swap
	@echo "Checking for apt dependencies..."
	@sudo apt-get update --allow-releaseinfo-change
	@for dep in $(APT_DEPENDENCIES); do \
		if ! dpkg -s $$dep > /dev/null 2>&1; then \
			sudo apt-get install -y $$dep; \
		fi \
	done

install_win_dependencies:
	cmd /c "(help npm > nul || exit 0) && where npm > nul 2> nul" || winget install -e --id OpenJS.NodeJS.LTS
	cmd /c "(help python > nul || exit 0) && where python > nul 2> nul" || winget install -e --name Python 3.10
	cmd /c "(help qckwinsvc > nul || exit 0) && where qckwinsvc > nul 2> nul" || npm install -g qckwinsvc

venv: flask_app/$(VENV_NAME)
flask_app/$(VENV_NAME):
	cd flask_app && python -m venv $(VENV_NAME)

updatepath:
	@if echo $$PATH | grep -q "/home/pi/.local/bin"; then \
		echo "PATH already contains /home/pi/.local/bin. No changes made."; \
	else \
		echo "export PATH=\$$PATH:/home/pi/.local/bin" >> ~/.bashrc; \
		. ~/.bashrc; \
	fi

kill: kill-flask kill-express

kill-express:
ifeq ($(OS),Windows_NT)
	qckwinsvc --name $(UI_SERVICE_NAME) --script vue/src/server/express_server.js --uninstall
else
	sudo nohup fuser -k 3000/tcp &
endif

kill-flask:
ifeq ($(OS),Windows_NT)
	-powershell.exe Start-Process -FilePath "flask_app/dist/win32_service/win32_service.exe" -Verb RunAs stop
else
	sudo nohup fuser -k 5000/tcp &
endif

directories:
	@chmod 777 ./
	@if [ ! -d "logs" ]; then \
		echo "Creating logs directory..."; \
		mkdir logs; \
		chmod 777 logs; \
	fi
	@if [ ! -d "db" ]; then \
		echo "Creating db directory..."; \
		mkdir db; \
		chmod 777 db; \
	fi

services-ctl: directories
	@echo "Checking for flask and vue services..."
	@if ! cmp services/flask/flask.service /etc/systemd/system/flask.service >/dev/null 2>&1; then \
		sudo cp services/flask/flask.service /etc/systemd/system/flask.service; \
		echo "Copied services/flask/flask.service to /etc/systemd/system/flask.service"; \
	fi
	if ! cmp services/vue/vue.service /etc/systemd/system/vue.service >/dev/null 2>&1; then \
		sudo cp services/vue/vue.service /etc/systemd/system/vue.service; \
		echo "Copied services/vue/vue.service to /etc/systemd/system/vue.service"; \
	fi
	@echo "Reloading systemctl daemon..."
	sudo systemctl daemon-reload
	@echo "Enabling flask and vue services..."
	sudo systemctl enable flask.service
	sudo systemctl enable vue.service
	@echo "Starting flask and vue services..."
	sudo systemctl start flask.service
	sudo systemctl start vue.service


update-full:
	git pull
	make install
	make kill

update-backend:
	git pull
	make install
	make kill-flask

update-frontend:
	git pull
	make install

push:
	git add .
	git commit -m "update"
	git push