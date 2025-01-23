# sudo apt-get install git
# git clone http://github.com/catalin-rusnac/replifactory_v7; cd replifactory_v7; make install

include /etc/environment

install: install-uv setup-uv install-pm2 setup-pm2 vps

install-git:
	if ! dpkg -s git > /dev/null; then \
		sudo apt-get install git -y; \
	fi

install-uv:
	if ! command -v uv > /dev/null; then \
		echo "Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		source "$HOME/.local/bin/env" \
	else \
		echo "uv already installed. No changes made."; \
	fi

setup-uv:
	if [ ! -d "flask_app/.venv" ]; then \
	  echo "Initializing UV in flask_app..."; \
	  uv init flask_app || { echo "Project already initialized. Skipping..."; }; \
	fi
	echo "Installing Python dependencies in flask_app..."
	cd flask_app && uv add -r requirements.txt
	if ! grep -q "include-system-site-packages = true" flask_app/.venv/pyvenv.cfg; then \
	  echo "Setting 'include-system-site-packages = true' in pyvenv.cfg..."; \
	  sed -i 's/include-system-site-packages = false/include-system-site-packages = true/' flask_app/.venv/pyvenv.cfg || echo "include-system-site-packages = true" >> flask_app/.venv/pyvenv.cfg; \
	else \
	  echo "'include-system-site-packages' is already set to true."; \
	fi

install-pm2:
	@if ! command -v npm > /dev/null; then \
		echo "Installing Node.js and npm for Raspberry Pi..."; \
		curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash \
		export NVM_DIR="$HOME/.nvm" \
		[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"; \
		nvm install 22 \
		echo "Node.js version: $$(node -v)"; \
		echo "npm version: $$(npm -v)"; \
	else \
		echo "Node.js and npm already installed. No changes made."; \
	fi
	if ! command -v pm2 > /dev/null; then \
		echo "Installing pm2 globally..."; \
		npm install pm2 -g; \
	else \
		echo "pm2 is already installed."; \
	fi; \
	if [ -d vue ]; then \
		echo "Installing npm dependencies for the 'vue' directory..."; \
		cd vue && npm install; \
	else \
		echo "'vue' directory not found. Skipping npm install."; \
	fi

setup-pm2:
	@echo "Starting PM2 with ecosystem.config.js..."
	pm2 start ecosystem.config.js || { echo "Failed to start PM2 with ecosystem.config.js"; exit 1; }
	@echo "Saving PM2 process list..."
	pm2 save || { echo "Failed to save PM2 process list"; exit 1; }
	@echo "Setting up PM2 to start on boot..."
	pm2 startup || { echo "Failed to set up PM2 startup script"; exit 1; }
	sudo env PATH=$$PATH:/home/pi/.nvm/versions/node/v22.13.0/bin \
		/home/pi/.nvm/versions/node/v22.13.0/lib/node_modules/pm2/bin/pm2 startup systemd -u pi --hp /home/pi || { echo "Failed to configure PM2 systemd startup"; exit 1; }
	@echo "Checking PM2 process status..."
	pm2 status || { echo "Failed to retrieve PM2 status"; exit 1; }

windows-install:
	cd vue && npm install -y
	cd flask_app && pip install -r requirements.txt

install-ngrok:
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


copy_to_www:
	@echo "Copying contents of vue/dist/ to /var/www/html..."
	@sudo cp -r vue/dist/* /var/www/html
	@echo "Copied contents of vue/dist/ to /var/www/html."

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

kill: kill-express kill-flask

kill-express:
	sudo nohup fuser -k 3000/tcp &

kill-flask:
	sudo nohup fuser -k 5000/tcp &

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

wifi_add_network:
	chmod 755 scripts/add_network.sh
	sudo scripts/add_network.sh

vps:
	#install autossh if not already installed
	if ! dpkg -s autossh > /dev/null; then \
		sudo apt-get install autossh -y; \
	fi
	if systemctl is-active --quiet autossh.service; then \
		sudo systemctl stop autossh.service; \
	fi
	sudo cp services/autossh.service /etc/systemd/system/autossh.service
	sudo systemctl daemon-reload
	sudo systemctl enable autossh.service
	sudo systemctl restart autossh.service

stunnel:
	#install stunnel if not already installed
	if ! dpkg -s stunnel4 > /dev/null; then \
		sudo apt-get install stunnel4 -y; \
	fi
	sudo cp services/stunnel.conf /etc/stunnel/stunnel.conf
	sudo cp services/stunnel.service /etc/systemd/system/stunnel.service

	sudo systemctl daemon-reload
	sudo systemctl enable stunnel.service
	sudo systemctl restart stunnel.service
	make vps

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
	flask db upgrade)
	# flask db migrate --app server.py

keygen:
	echo "run ssh-keygen -t rsa -b 4096 -C \"pi@$(RASPBERRY_NAME)\" -f ~/.ssh/id_rsa -N \"\"; cat ~/.ssh/id_rsa.pub"

timelapse:
	if ps -ef | grep -v grep | grep timelapse.py ; then
		echo "timelapse.py is already running"
		exit 0
	fi
	FOLDER=$(date +%Y%m%d)
	mkdir -p /home/pi/timelapse/$FOLDER
	nohup /home/pi/timelapse/timelapse.py --outputdir /home/pi/timelapse/$FOLDER &

timezone:
	chmod +x scripts/update_timezone.sh
	sudo scripts/update_timezone.sh

pull-update: pull-nokill
	make kill

pull-nokill:
	git reset --hard
	git pull
	sudo apt-get update
	make timezone
	make migrate
	make stunnel
	make services-ctl

update-nmsu:
	git pull
	sudo apt-get update
	make timezone
	make pip
	make migrate
	make stunnel
	make kill

clean-memory:
	du -h --max-depth=1
	sudo apt-get clean
	pip cache purge
	npm cache clean
#   npm cache clean --force
	npm cache verify
	sudo journalctl --disk-usage
	sudo journalctl --vacuum-size=500M
	du -h --max-depth=1

update_and_restart_experiment:
	@sudo chmod +x scripts/update_and_restart_experiment.py
	@nohup sudo python3 scripts/update_and_restart_experiment.py &

update-autofix:
	@sudo nohup make wifi_add_network &