#cd; git clone http://github.com/catalin-rusnac/replifactory_v7; cd replifactory_v7; make install
include /etc/environment
install: check_env_variables install_apt_dependencies node-pi updatepath pip ngrok dwservice_install
	cd vue && npm install -y;
	cd flask_app && pip install -r requirements.txt;
	make services-ctl

windows-install:
	cd vue && npm install -y
	cd flask_app && pip install -r requirements.txt

run: run-flask run-express

run-flask:
	python flask_app/server.py &

run-express:
	node vue/src/server/express_server.js &

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

APT_DEPENDENCIES = python3-distutils python3-scipy python3-numpy python3-pandas libatlas-base-dev python3-dev gfortran libopenblas-dev autossh

install_apt_dependencies: swap
	@echo "Checking for apt dependencies..."
	@sudo apt-get update --allow-releaseinfo-change
	@for dep in $(APT_DEPENDENCIES); do \
		if ! dpkg -s $$dep > /dev/null 2>&1; then \
			sudo apt-get install -y $$dep; \
		fi \
	done

updatepath:
	@if echo $$PATH | grep -q "/home/pi/.local/bin"; then \
		echo "PATH already contains /home/pi/.local/bin. No changes made."; \
	else \
		echo "export PATH=\$$PATH:/home/pi/.local/bin" >> ~/.bashrc; \
		. ~/.bashrc; \
	fi

kill: kill-flask kill-express

kill-express:
	sudo nohup fuser -k 3000/tcp &

kill-flask:
	sudo nohup fuser -k 5000/tcp &

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
	make migrate
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


dwservice_install:

	cd services
	if [ ! -f dwagent.sh ]; then \
		wget https://www.dwservice.net/download/dwagent.sh; \
	fi
	chmod +x ./services/dwagent.sh

dwservice_run:
	sudo ./services/dwagent.sh -silent key=$(DWSERVICE_KEY)

wifi_new_config:
	sudo cp services/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf
	sudo chmod 600 /etc/wpa_supplicant/wpa_supplicant.conf
	sudo systemctl restart dhcpcd

vps:
	if systemctl is-active --quiet autossh.service; then \
		sudo systemctl stop autossh.service; \
	fi
	sudo cp services/autossh.service /etc/systemd/system/autossh.service
	sudo systemctl daemon-reload
	sudo systemctl enable autossh.service
	sudo systemctl restart autossh.service

check_env_variables:
	@echo "Setting up " $(RASPBERRY_NAME)": "$(VPS_IP)":"$(VPS_PORT)"..."

update-hostname:
	@echo "Setting hostname to $(RASPBERRY_NAME)"
	@echo "$(RASPBERRY_NAME)" | sudo tee /etc/hostname
	@sudo sed -i "s/127.0.1.1.*/127.0.1.1       $(RASPBERRY_NAME)/" /etc/hosts
	@echo "Hostname updated. You may need to reboot for changes to take effect."

secrets:
	make dwservice_run
	make update-hostname
	sudo systemctl daemon-reload
	#ssh-keygen -t rsa -b 4096 -C "pi@$HOSTNAME" -f ~/.ssh/id_rsa -N ""; cat ~/.ssh/id_rsa.pub
	#ssh-copy-id -i ~/.ssh/id_rsa.pub replifactory-device@$(VPS_IP)   << do this manually, then ssh into the vps and add the public key to the authorized_keys file
	#make vps

	echo $HOSTNAME > .env

migrate:
	(cd flask_app && \
	export FLASK_APP=./server.py && \
	if ! echo $$PYTHONPATH | grep -q "$$PWD"; then \
		export PYTHONPATH=$$PYTHONPATH:$$PWD; \
	fi && \
	if ! pip show Flask-Migrate > /dev/null; then \
		pip install Flask-Migrate; \
	fi && \
	flask db migrate && \
	flask db upgrade)

timelapse:
	if ps -ef | grep -v grep | grep timelapse.py ; then
		echo "timelapse.py is already running"
		exit 0
	fi
	FOLDER=$(date +%Y%m%d)
	mkdir -p /home/pi/timelapse/$FOLDER
	nohup /home/pi/timelapse/timelapse.py --outputdir /home/pi/timelapse/$FOLDER &