# Install system dependencies
# Use Ubuntu as base image for better libseccomp support
FROM ubuntu:latest

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl build-essential pkg-config libssl-dev python3 python3-pip \
        git ca-certificates llvm file openssh-client git-lfs \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs/ | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy parent directory contents (since dockerfile is in docker/ subdirectory)
COPY ../ .

# Make build script executable and run it
# RUN chmod +x build.sh && ./build.sh --release

# Set the default command
CMD ["bash"]