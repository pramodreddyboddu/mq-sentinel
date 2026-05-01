# MQ-Sentinel — convenience targets. Real work happens in CI; this just
# wraps the common loops.

VERSION    := $(shell awk -F'"' '/^__version__/ {print $$2}' src/mq_sentinel/__init__.py)
IMAGE      ?= ghcr.io/pramodreddyboddu/mq-sentinel
TAG        ?= $(VERSION)
ARCH       ?= x86_64
DIST_DIR   := dist
PKG_DIR    := $(DIST_DIR)/pkg

.PHONY: help install dev test lint type security ci docker rpm deb pkg clean release

help:                ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:             ## Install Python deps + editable package (uv)
	uv sync --all-extras --dev
	uv pip install -e .

dev: install         ## Alias for install + run unit tests
	$(MAKE) test

test:                ## Run pytest
	uv run pytest -q

lint:                ## Run ruff
	uv run ruff check .
	uv run ruff format --check .

type:                ## Run mypy (strict)
	uv run mypy

security:            ## Run security-marked tests only
	uv run pytest -q -m security

ci: lint type test security  ## Full CI gauntlet (everything that runs in GHA)

docker:              ## Build the production image
	docker build -f deploy/Dockerfile -t $(IMAGE):$(TAG) .

rpm: install         ## Build an RPM via fpm (requires fpm + ruby)
	@command -v fpm >/dev/null || { echo "fpm not installed. gem install fpm"; exit 1; }
	mkdir -p $(PKG_DIR)
	rm -rf $(DIST_DIR)/rootfs
	uv run python -m build --wheel
	mkdir -p $(DIST_DIR)/rootfs/opt/mq-sentinel
	python3.12 -m venv $(DIST_DIR)/rootfs/opt/mq-sentinel
	$(DIST_DIR)/rootfs/opt/mq-sentinel/bin/pip install --upgrade pip wheel
	$(DIST_DIR)/rootfs/opt/mq-sentinel/bin/pip install dist/mq_sentinel-*.whl
	mkdir -p $(DIST_DIR)/rootfs/etc/mq-sentinel/secrets
	mkdir -p $(DIST_DIR)/rootfs/etc/mq-sentinel/inventory
	mkdir -p $(DIST_DIR)/rootfs/var/log/mq-sentinel
	mkdir -p $(DIST_DIR)/rootfs/usr/lib/systemd/system
	mkdir -p $(DIST_DIR)/rootfs/usr/bin
	cp packaging/systemd/mq-sentinel.service $(DIST_DIR)/rootfs/usr/lib/systemd/system/
	cp packaging/systemd/mq-sentinel.env     $(DIST_DIR)/rootfs/etc/mq-sentinel/
	ln -sf /opt/mq-sentinel/bin/mq-sentinel  $(DIST_DIR)/rootfs/usr/bin/mq-sentinel
	fpm -s dir -t rpm \
	    -n mq-sentinel \
	    -v $(VERSION) \
	    --license "Proprietary" \
	    --vendor "MG" \
	    --maintainer "MG <noreply@example.com>" \
	    --url "https://github.com/pramodreddyboddu/mq-sentinel" \
	    --description "Read-only IBM MQ diagnostic MCP server" \
	    --architecture $(ARCH) \
	    --depends "python3.12 >= 3.12" \
	    --depends "systemd" \
	    --before-install packaging/deb/postinst \
	    --after-install packaging/deb/postinst \
	    --before-remove packaging/deb/prerm \
	    --config-files /etc/mq-sentinel/mq-sentinel.env \
	    --rpm-summary "MQ-Sentinel" \
	    --rpm-os linux \
	    -p $(PKG_DIR)/ \
	    -C $(DIST_DIR)/rootfs \
	    .

deb: install         ## Build a .deb via fpm
	@command -v fpm >/dev/null || { echo "fpm not installed. gem install fpm"; exit 1; }
	mkdir -p $(PKG_DIR)
	rm -rf $(DIST_DIR)/rootfs
	uv run python -m build --wheel
	mkdir -p $(DIST_DIR)/rootfs/opt/mq-sentinel
	python3.12 -m venv $(DIST_DIR)/rootfs/opt/mq-sentinel
	$(DIST_DIR)/rootfs/opt/mq-sentinel/bin/pip install --upgrade pip wheel
	$(DIST_DIR)/rootfs/opt/mq-sentinel/bin/pip install dist/mq_sentinel-*.whl
	mkdir -p $(DIST_DIR)/rootfs/etc/mq-sentinel/secrets
	mkdir -p $(DIST_DIR)/rootfs/etc/mq-sentinel/inventory
	mkdir -p $(DIST_DIR)/rootfs/var/log/mq-sentinel
	mkdir -p $(DIST_DIR)/rootfs/lib/systemd/system
	mkdir -p $(DIST_DIR)/rootfs/usr/bin
	cp packaging/systemd/mq-sentinel.service $(DIST_DIR)/rootfs/lib/systemd/system/
	cp packaging/systemd/mq-sentinel.env     $(DIST_DIR)/rootfs/etc/mq-sentinel/
	ln -sf /opt/mq-sentinel/bin/mq-sentinel  $(DIST_DIR)/rootfs/usr/bin/mq-sentinel
	fpm -s dir -t deb \
	    -n mq-sentinel \
	    -v $(VERSION) \
	    --license "Proprietary" \
	    --vendor "MG" \
	    --maintainer "MG <noreply@example.com>" \
	    --url "https://github.com/pramodreddyboddu/mq-sentinel" \
	    --description "Read-only IBM MQ diagnostic MCP server" \
	    --architecture amd64 \
	    --depends "python3.12 (>= 3.12)" \
	    --depends "systemd" \
	    --after-install packaging/deb/postinst \
	    --before-remove packaging/deb/prerm \
	    --config-files /etc/mq-sentinel/mq-sentinel.env \
	    -p $(PKG_DIR)/ \
	    -C $(DIST_DIR)/rootfs \
	    .

pkg: rpm deb         ## Build all OS packages

release: ci docker pkg  ## Full release pipeline (run in CI)
	@echo "Release artifacts in $(DIST_DIR):"
	@ls -la $(DIST_DIR) $(PKG_DIR) 2>/dev/null || true

clean:               ## Remove build artifacts
	rm -rf $(DIST_DIR) build *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov coverage.xml
	find . -name __pycache__ -type d -exec rm -rf {} +
