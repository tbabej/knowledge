test:
	- mkdir -p /tmp/knowledge-coverage
	- docker-compose up --exit-code-from tests
