BINARY     := pipguard
BUILD_DIR  := build
LDFLAGS    := -s -w
PKG        := ./...

.PHONY: all build cross test clean install uninstall vet fmt

all: build

build:
	go build -ldflags="$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY) .

cross:
	GOOS=linux  GOARCH=amd64 go build -ldflags="$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY)-linux-amd64  .
	GOOS=linux  GOARCH=arm64 go build -ldflags="$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY)-linux-arm64  .
	GOOS=darwin GOARCH=amd64 go build -ldflags="$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY)-darwin-amd64 .
	GOOS=darwin GOARCH=arm64 go build -ldflags="$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY)-darwin-arm64 .

test:
	go test -v $(PKG)

vet:
	go vet $(PKG)

fmt:
	gofmt -l .

install: build
	bash scripts/install.sh

uninstall:
	bash scripts/uninstall.sh

clean:
	rm -rf $(BUILD_DIR)
