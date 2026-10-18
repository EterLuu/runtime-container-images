ARG BASE_IMAGE=nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.title="Self-hosted CUDA development environment" \
      org.opencontainers.image.description="Ubuntu 24.04, CUDA 12.8, PyTorch and ML development tools"

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    CUDA_HOME=/usr/local/cuda \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:/usr/local/cuda/bin:${PATH} \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH} \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/root/.cache/huggingface \
    TORCH_HOME=/root/.cache/torch

USER root

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        autoconf \
        automake \
        aria2 \
        bash-completion \
        build-essential \
        bzip2 \
        ca-certificates \
        ccache \
        clang \
        cmake \
        curl \
        dnsutils \
        dumb-init \
        ffmpeg \
        file \
        gdb \
        git \
        git-lfs \
        gfortran \
        htop \
        iproute2 \
        iputils-ping \
        jq \
        less \
        libaio-dev \
        libbz2-dev \
        libffi-dev \
        libjpeg-dev \
        liblapack-dev \
        liblzma-dev \
        libncurses-dev \
        libnuma-dev \
        libopenblas-dev \
        libopenmpi-dev \
        libpng-dev \
        libreadline-dev \
        libsqlite3-dev \
        libssl-dev \
        libtool \
        libxml2-dev \
        libxmlsec1-dev \
        llvm \
        locales \
        lsof \
        nano \
        net-tools \
        netcat-openbsd \
        ninja-build \
        numactl \
        nvtop \
        openmpi-bin \
        openssh-client \
        openssh-server \
        p7zip-full \
        patchelf \
        pciutils \
        pkg-config \
        procps \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        rsync \
        ripgrep \
        screen \
        software-properties-common \
        strace \
        sudo \
        tar \
        tmux \
        tree \
        unzip \
        usbutils \
        valgrind \
        vim \
        wget \
        xz-utils \
        zip \
        zlib1g-dev \
        zstd; \
    locale-gen en_US.UTF-8; \
    git lfs install --system; \
    mkdir -p /run/sshd /workspace /data /var/lib/self-host; \
    chmod 0700 /var/lib/self-host; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

ARG TORCH_VERSION=2.9.1
ARG TORCHVISION_VERSION=0.24.1
ARG TORCHAUDIO_VERSION=2.9.1
ARG PYTORCH_CUDA_INDEX_URL=https://download.pytorch.org/whl/cu128

RUN set -eux; \
    python3 -m venv "${VIRTUAL_ENV}"; \
    python -m pip install --upgrade pip setuptools wheel packaging; \
    python -m pip install \
        --index-url "${PYTORCH_CUDA_INDEX_URL}" \
        "torch==${TORCH_VERSION}" \
        "torchvision==${TORCHVISION_VERSION}" \
        "torchaudio==${TORCHAUDIO_VERSION}"; \
    printf '%s\n' \
        "torch==${TORCH_VERSION}" \
        "torchvision==${TORCHVISION_VERSION}" \
        "torchaudio==${TORCHAUDIO_VERSION}" \
        "numpy<2.0" \
        > "${VIRTUAL_ENV}/pip-constraints.txt"; \
    export PIP_CONSTRAINT="${VIRTUAL_ENV}/pip-constraints.txt"; \
    python -m pip install \
        accelerate \
        datasets \
        einops \
        huggingface-hub \
        ipykernel \
        jupyterlab==4.4.10 \
        librosa \
        lightgbm \
        matplotlib \
        numpy \
        onnx \
        onnxruntime-gpu \
        opencv-python-headless \
        pandas \
        pillow \
        psutil \
        pyyaml \
        requests \
        rich \
        safetensors \
        scikit-learn \
        scipy \
        seaborn \
        sentencepiece \
        tensorboard \
        tokenizers \
        tqdm \
        transformers \
        uv \
        xgboost; \
    python -m ipykernel install \
        --prefix "${VIRTUAL_ENV}" \
        --name pytorch-cu128 \
        --display-name "PyTorch CUDA 12.8"; \
    python -c 'import torch; print("torch:", torch.__version__); print("torch cuda:", torch.version.cuda)'

ENV PIP_CONSTRAINT=/opt/venv/pip-constraints.txt

COPY --chmod=755 scripts/self-host-entrypoint.sh /usr/local/bin/self-host-entrypoint.sh

RUN set -eux; \
    mkdir -p /root/.ssh; \
    printf '%s\n' \
        'source /opt/venv/bin/activate' \
        'export PATH=/usr/local/cuda/bin:${PATH}' \
        > /root/.bashrc; \
    printf '%s\n' \
        'Host *' \
        '  ServerAliveInterval 30' \
        '  ServerAliveCountMax 3' \
        > /root/.ssh/config; \
    chmod 0644 /root/.bashrc; \
    chmod 0600 /root/.ssh/config

WORKDIR /workspace

EXPOSE 22 6006 8888

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD sshd -t && pgrep -x sshd >/dev/null || exit 1

ENTRYPOINT ["/usr/bin/dumb-init", "--", "/usr/local/bin/self-host-entrypoint.sh"]
CMD ["sleep", "infinity"]
