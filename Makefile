install: ngrok swap node-pi pip
	cd vue && npm install
	cd flask && pip install -r requirements.txt

run: run-flask run-express

run-flask:
	python flask/server.py &

run-express:
	node vue/src/server/express_server.js &

run-vue-dev:
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
	    sudo apt-get install python3-distutils
		echo "Installing pip..."; \
		curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py; \
		sudo python3 get-pip.py; \
		rm get-pip.py; \
	fi

copy_to_www:
	@echo "Copying contents of vue/dist/ to /var/www/html..."
	@sudo cp -r vue/dist/* /var/www/html
	@echo "Copied contents of vue/dist/ to /var/www/html."

APT_DEPENDENCIES = python3-distutils libatlas-base-dev python3-dev gfortran

install_apt_dependencies: swap
	@echo "Checking for apt dependencies..."
	@sudo apt-get update --allow-releaseinfo-change
	@for dep in $(APT_DEPENDENCIES); do \
		if ! dpkg -s $$dep > /dev/null 2>&1; then \
			sudo apt-get install -y $$dep; \
		fi \
	done
