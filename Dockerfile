# Install system dependencies
# Use Ubuntu as base image for better libseccomp support
FROM ubuntu:latest

# Install system dependencies.
# Importantly, this installs gcc for cross-compilation to ARM and x86.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl build-essential pkg-config libssl-dev python3 python3-pip \
        git ca-certificates llvm file openssh-client git-lfs \
        gcc-i686-linux-gnu \
        g++-i686-linux-gnu \
        gcc-arm-linux-gnueabihf \
        docker.io \
    && rm -rf /var/lib/apt/lists/*
# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs/ | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

COPY . .

# Add Rust targets for cross-compilation
RUN rustup target add i686-unknown-linux-gnu \
    && rustup target add armv7-unknown-linux-gnueabihf \
    && rustup target add riscv32i-unknown-none-elf

# Install cross
RUN cargo install cross --git https://github.com/cross-rs/cross

RUN pip3 install --break-system-packages -r python/requirements.txt


# Make build script executable and run it
# RUN chmod +x build.sh && ./build.sh --release

# Set the default command
CMD ["bash"]