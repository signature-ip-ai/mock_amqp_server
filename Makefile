VENV_DIR := .pyvenv

.ONESHELL:


build:
	@ pip3 install --upgrade build
	@ python3 -m build


install: uninstall build
	@ pip3 install dist/*.whl


uninstall:
	@ pip3 uninstall -y mock_amqp_server


$(VENV_DIR):
	@ echo "Creating a virtual environment ..."
	@ python3 -m venv $(VENV_DIR)


clean:
	@ rm -rf src/mock_amqp_server.egg-info dist
