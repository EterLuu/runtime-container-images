ARG BASE_IMAGE=nvidia/cuda:11.3.1-cudnn8-devel-ubuntu20.04
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

# V100 = Volta = sm_70
ENV TORCH_CUDA_ARCH_LIST="7.0"
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

ENV CUDA_HOME=/usr/local/cuda
ENV PATH=/usr/local/cuda/bin:${PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}

USER root

# Config apt source to Huawei Cloud and install packages
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then \
        cp -a /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak; \
        sed -i 's@http://[^ ]*archive.ubuntu.com@http://mirrors.huaweicloud.com@g' /etc/apt/sources.list.d/ubuntu.sources; \
        sed -i 's@http://[^ ]*security.ubuntu.com@http://mirrors.huaweicloud.com@g' /etc/apt/sources.list.d/ubuntu.sources; \
        sed -i 's@http://ports.ubuntu.com/ubuntu-ports@http://mirrors.huaweicloud.com/ubuntu-ports@g' /etc/apt/sources.list.d/ubuntu.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
        cp -a /etc/apt/sources.list /etc/apt/sources.list.bak; \
        sed -i 's@http://[^ ]*archive.ubuntu.com@http://mirrors.huaweicloud.com@g' /etc/apt/sources.list; \
        sed -i 's@http://[^ ]*security.ubuntu.com@http://mirrors.huaweicloud.com@g' /etc/apt/sources.list; \
        sed -i 's@http://ports.ubuntu.com/ubuntu-ports@http://mirrors.huaweicloud.com/ubuntu-ports@g' /etc/apt/sources.list; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        openssh-client \
        openssh-server \
        iputils-ping \
        net-tools \
        sudo \
        ffmpeg \
        curl \
        wget \
        ca-certificates \
        git \
        vim \
        less \
        bash-completion \
        htop \
        p7zip-full \
        tmux \
        dumb-init \
        build-essential \
        ninja-build \
        pkg-config \
        cmake \
        python3-dev; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

# Create ma-group / ma-user
RUN set -eux; \
    existing_user="$(getent passwd 1000 | awk -F ':' '{print $1}' || true)"; \
    existing_group="$(getent group 100 | awk -F ':' '{print $1}' || true)"; \
    if [ -n "${existing_user}" ] && [ "${existing_user}" != "ma-user" ]; then \
        userdel -r "${existing_user}" || true; \
    fi; \
    if [ -n "${existing_group}" ] && [ "${existing_group}" != "ma-group" ]; then \
        groupmod -n ma-group "${existing_group}"; \
    elif [ -z "${existing_group}" ]; then \
        groupadd -g 100 ma-group; \
    fi; \
    if ! id ma-user >/dev/null 2>&1; then \
        useradd -d /home/ma-user -m -u 1000 -g 100 -s /bin/bash ma-user; \
    fi; \
    chmod -R 750 /home/ma-user

# Allow ma-user to use sudo
RUN set -eux; \
    echo 'ma-user ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ma-user; \
    chmod 0440 /etc/sudoers.d/ma-user

# Install OpenSSH for ModelArts
RUN set -eux; \
    ssh -V; \
    mkdir -p /run/sshd; \
    chmod 0755 /run/sshd

# Install code-server 4.x
ARG CODE_SERVER_VERSION=4.20.1

RUN set -eux; \
    apt-get update; \
    ARCH="$(dpkg --print-architecture)"; \
    case "${ARCH}" in \
        amd64) CODE_SERVER_ARCH="amd64" ;; \
        arm64) CODE_SERVER_ARCH="arm64" ;; \
        *) echo "Unsupported architecture for code-server: ${ARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fL \
        -o /tmp/code-server.deb \
        "https://gh-proxy.org/https://github.com/coder/code-server/releases/download/v${CODE_SERVER_VERSION}/code-server_${CODE_SERVER_VERSION}_${CODE_SERVER_ARCH}.deb"; \
    apt-get install -y /tmp/code-server.deb; \
    rm -f /tmp/code-server.deb; \
    code-server --version; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

# Add ssh auto start
COPY --chmod=755 scripts/start_sshd.sh /usr/local/bin/start_sshd.sh
COPY --chmod=755 scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

ENV MY_SSHD_PORT=38888

# Switch to ma-user and install Miniconda
USER ma-user

RUN set -eux; \
    ARCH="$(uname -m)"; \
    case "$ARCH" in \
        x86_64) MINICONDA_ARCH="x86_64" ;; \
        aarch64) MINICONDA_ARCH="aarch64" ;; \
        *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;; \
    esac; \
    wget --no-check-certificate -O /tmp/miniconda.sh \
        "https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-${MINICONDA_ARCH}.sh"; \
    bash /tmp/miniconda.sh -b -u -p /home/ma-user/miniconda; \
    rm -f /tmp/miniconda.sh; \
    /home/ma-user/miniconda/bin/conda clean -afy

ENV PATH=/home/ma-user/miniconda/bin:${PATH}

# Configure conda and pip sources
RUN set -eux; \
    mkdir -p /home/ma-user/.pip; \
    printf '%s\n' \
      'channels:' \
      '  - defaults' \
      'show_channel_urls: true' \
      'default_channels:' \
      '  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main' \
      '  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r' \
      '  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2' \
      'custom_channels:' \
      '  conda-forge: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud' \
      '  pytorch: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud' \
      > /home/ma-user/.condarc; \
    printf '%s\n' \
      '[global]' \
      'index-url = https://mirrors.huaweicloud.com/repository/pypi/simple' \
      'trusted-host = mirrors.huaweicloud.com' \
      'timeout = 120' \
      > /home/ma-user/.pip/pip.conf

# Create CUDA/PyTorch environment for V100
# The ipykernel package is mandatory for starting a kernel.
SHELL ["/bin/bash", "-lc"]

ARG PYPI_INDEX_URL=https://mirrors.huaweicloud.com/repository/pypi/simple
ARG PYPI_TRUSTED_HOST=mirrors.huaweicloud.com
ARG PYTORCH_STABLE_URL=https://download.pytorch.org/whl/torch_stable.html

# Can be overwritted：
# docker build --build-arg TORCH_VERSION=2.7.1 ...
ARG TORCH_VERSION=1.12.1+cu113
ARG TORCHVISION_VERSION=0.13.1+cu113
ARG TORCHAUDIO_VERSION=0.12.1
ARG PYTHON_VERSION=3.10

RUN set -eux; \
    source /home/ma-user/miniconda/etc/profile.d/conda.sh; \
    \
    conda create -y --name torch-1.12.1 python=${PYTHON_VERSION} pip "numpy<2.0"; \
    printf '%s\n' \
        "torch==${TORCH_VERSION}" \
        "torchvision==${TORCHVISION_VERSION}" \
        "torchaudio==${TORCHAUDIO_VERSION}" \
        "numpy<2.0" \
        > /tmp/pip-constraints.txt; \
    \
    export PIP_CONSTRAINT=/tmp/pip-constraints.txt; \
    \
    conda activate torch-1.12.1; \
    \
    python -m pip install --upgrade pip wheel setuptools pyyaml packaging; \
    \
    python -m pip install --no-cache-dir --no-index \
        -f "${PYTORCH_STABLE_URL}" \
        "torch==${TORCH_VERSION}" \
        "torchvision==${TORCHVISION_VERSION}" \
        "torchaudio==${TORCHAUDIO_VERSION}"; \
    \
    DS_BUILD_OPS=0 python -m pip install --no-cache-dir \
        -i "${PYPI_INDEX_URL}" \
        --trusted-host "${PYPI_TRUSTED_HOST}" \
        "numpy<2.0" \
        "ipykernel>=6.29,<7" \
        "transformers>=4.30,<4.39" \
        "accelerate>=0.20,<0.29" \
        "deepspeed>=0.9,<0.13" \
        "librosa>=0.9,<0.11" \
        "tqdm" \
        "datasets>=2.12,<2.19" \
        "sentencepiece" \
        "safetensors>=0.3,<0.5" \
        "tokenizers>=0.13,<0.16" \
        "einops" \
        "scipy" \
        "scikit-learn" \
        "pandas" \
        "matplotlib" \
        "pillow" \
        "psutil"; \
    \
    python -m ipykernel install \
        --user \
        --name torch-1.12.1 \
        --display-name "torch-1.12.1"; \
    \
    python -c 'import torch; print("torch:", torch.__version__); print("torch cuda:", torch.version.cuda); print("cuda available during build:", torch.cuda.is_available())'; \
    conda deactivate; \
    conda clean -afy; \
    rm -rf /home/ma-user/.cache/pip; \
    \
    echo 'source /home/ma-user/miniconda/etc/profile.d/conda.sh' >> /home/ma-user/.bashrc; \
    echo 'conda activate torch-1.12.1' >> /home/ma-user/.bashrc

ENV CONDA_DEFAULT_ENV=torch-1.12.1
ENV PATH=/home/ma-user/miniconda/envs/torch-1.12.1/bin:/home/ma-user/miniconda/bin:${PATH}

USER ma-user
WORKDIR /home/ma-user

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["bash"]
