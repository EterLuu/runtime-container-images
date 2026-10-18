# Runtime Container Images

本仓库维护面向 ModelArts 和 self-host 场景的多运行环境镜像，当前包含 CANN 和 CUDA 镜像，并集成 GitHub Actions 构建、发布和批量发布流程。

## 目录结构

```text
images/<platform>/<runtime>/<tag>/Dockerfile # 镜像构建上下文
images/<platform>/<runtime>/scripts/         # 构建前复制到同类镜像上下文的运行时脚本
image_publish_version.json                   # 可选元数据：衍生芯片、别名 tag、平台和 runner
scripts/image_metadata.py                    # CI 和本地脚本共用的元数据解析工具
scripts/prepare_image_context.sh             # 构建前同步同类 scripts 到目标上下文
scripts/build_image.sh                       # 本地构建脚本
scripts/publish_image.sh                     # 本地 buildx 发布脚本
examples/self-host-cuda/                     # Self-host Compose 示例和使用说明
.github/workflows/build_images.yml
.github/workflows/build_and_push_image.yml
.github/workflows/batch_build_and_push_images.yml
.github/workflows/push_existing_image.yml
```

目录前两级用于发布分类：`images/modelarts/cann/...` 发布到 `modelarts-cann`，`images/modelarts/cuda/...` 发布到 `modelarts-cuda`，`images/self-host/cuda/...` 发布到 `self-host-cuda`。

## 当前镜像

| 分类             | 标签                      | 基础镜像                                      | 默认用户  |
| ---------------- | ------------------------- | --------------------------------------------- | --------- |
| `modelarts-cann` | `9.1.1-910b-ubuntu22.04` | `ascendai/cann:9.1.1-910b-ubuntu22.04-py3.11` | `ma-user` |
| `modelarts-cann` | `9.1.1-310p-ubuntu22.04` | `ascendai/cann:9.1.1-310p-ubuntu22.04-py3.11` | `ma-user` |
| `modelarts-cann` | `9.1.1-910-ubuntu22.04`  | `ascendai/cann:9.1.1-910-ubuntu22.04-py3.11`  | `ma-user` |
| `modelarts-cann` | `9.1.1-950-ubuntu22.04`  | `ascendai/cann:9.1.1-950-ubuntu22.04-py3.11`  | `ma-user` |
| `modelarts-cann` | `9.1.1-a3-ubuntu22.04`   | `ascendai/cann:9.1.1-a3-ubuntu22.04-py3.11`   | `ma-user` |
| `modelarts-cann` | `9.0.0-910b-ubuntu22.04`  | `ascendai/cann:9.0.0-910b-ubuntu22.04-py3.11` | `ma-user` |
| `modelarts-cann` | `9.0.0-310p-ubuntu22.04`  | `ascendai/cann:9.0.0-310p-ubuntu22.04-py3.11` | `ma-user` |
| `modelarts-cann` | `9.0.0-910-ubuntu22.04`   | `ascendai/cann:9.0.0-910-ubuntu22.04-py3.11`  | `ma-user` |
| `modelarts-cann` | `9.0.0-950-ubuntu22.04`   | `ascendai/cann:9.0.0-950-ubuntu22.04-py3.11`  | `ma-user` |
| `modelarts-cann` | `9.0.0-a3-ubuntu22.04`    | `ascendai/cann:9.0.0-a3-ubuntu22.04-py3.11`   | `ma-user` |
| `modelarts-cuda` | `11.3.1-v100-ubuntu20.04` | `nvidia/cuda:11.3.1-cudnn8-devel-ubuntu20.04` | `ma-user` |
| `modelarts-cuda` | `12.6.1-v100-ubuntu24.04` | `nvidia/cuda:12.6.1-cudnn-devel-ubuntu24.04`  | `ma-user` |
| `self-host-cuda` | `12.8.1-ubuntu24.04`      | `nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04` | `root`    |

CANN 的 `9.1.1-910b-ubuntu22.04` 和 `9.0.0-910b-ubuntu22.04` 是模板目录，其它芯片版本由 `derived_chips` 自动展开，构建时仅替换 Dockerfile 顶层 `BASE_IMAGE`。9.1.1 默认使用 `torch-2.12`，并提供 CANN 9.1.X 对应的 TorchNPU 26.1.1 兼容环境。CUDA 样例没有配置 `derived_chips`，会按实际目录直接构建。

CANN、ModelArts CUDA 和 self-host CUDA 镜像会在运行时启用对应环境的 pip constraint，保护 PyTorch、TorchVision、TorchAudio 和 NumPy 的版本；切换 CANN conda 环境时会自动切换到该环境自己的约束文件。

构建前会把同类型目录下的 `scripts/` 复制到目标构建目录的 `scripts/` 下，例如 `images/modelarts/cuda/scripts` 会复制到 `images/modelarts/cuda/<tag>/scripts`。

## 本地构建

先校验元数据和 Dockerfile 路径：

```bash
python3 scripts/image_metadata.py validate
```

构建单个 tag：

```bash
IMAGE_REPOSITORY=modelarts-cann \
  scripts/build_image.sh 9.0.0-310p-ubuntu22.04

IMAGE_REPOSITORY=modelarts-cuda \
  scripts/build_image.sh 11.3.1-v100-ubuntu20.04

IMAGE_REPOSITORY=modelarts-cuda \
  scripts/build_image.sh 12.6.1-v100-ubuntu24.04

IMAGE_REPOSITORY=self-host-cuda \
  scripts/build_image.sh 12.8.1-ubuntu24.04
```

## Self-host 使用

CUDA 12.8 self-host 镜像包含 Ubuntu 24.04、CUDA/cuDNN 开发环境、Python 3.12、PyTorch 2.9.1/cu128、常用机器学习包、编译工具和 SSH 服务。Compose 示例提供 GPU 映射、CPU/内存/PID/共享内存限制，以及 root home、workspace、数据目录和初始化状态持久化：

```bash
cd examples/self-host-cuda
cp .env.example .env
mkdir -p projects data
docker compose up -d
ssh -p 2222 root@localhost
```

`INITIAL_ROOT_PASSWORD` 只在首次初始化时生效。初始化后应从 `.env` 删除密码并重建容器，使明文密码不再保留在容器环境中。完整配置、安全说明和“持久化整个容器”的缺点见 [examples/self-host-cuda/README.md](examples/self-host-cuda/README.md)。

发布镜像：

```bash
docker login ghcr.io
IMAGE_REPOSITORIES=ghcr.io/<owner> \
  scripts/publish_image.sh 9.0.0-910b-ubuntu22.04
```

每次发布会让基础版本 tag、带 Release 标记的 tag 和 `latest` 指向同一个镜像，例如 `9.0.0-910b-ubuntu22.04`、`9.0.0-910b-ubuntu22.04-r260716.122328` 和 `latest`。Release 标记格式为 `rYYMMDD.HHMMSS`；本地发布可通过 `RELEASE_TIMESTAMP=YYMMDD.HHMMSS` 指定，批量发布中的所有镜像共享同一个时间戳。批量发布多个镜像到同一仓库时，`latest` 最终指向最后完成发布的镜像。

`IMAGE_REPOSITORIES` 支持逗号或空白分隔的多个仓库。可以填写完整仓库，也可以只填写命名空间，脚本会按目录分类补齐末级仓库名：

```bash
IMAGE_REPOSITORIES="ghcr.io/<owner>,docker.io/<namespace>,swr.cn-southwest-2.myhuaweicloud.com/<organization>"
```

## GitHub Actions

- `Build Images`：PR 或 push 修改 `images/**` 时自动构建实际存在的 `images/<platform>/<runtime>/<tag>` 目录，不展开 `derived_chips`，不推送镜像。
- `Build and Publish Image`：手动或被其它 workflow 调用，支持只构建或构建并发布指定 tag。
- `Batch Build and Publish Images`：按 `image_version` 批量调用发布 workflow，会展开 CANN 的 `derived_chips`。
- `Push Existing Docker Image`：单独登录指定 Docker 仓库，并推送 runner 上已经存在的镜像。

`Push Existing Docker Image` 是独立的手动 workflow。填写仓库或组织前缀、登录命令和本地镜像名即可；workflow 会自动生成目标镜像名，例如：

```text
registry: docker.io/<owner>
login_command: printf '%s\n' '<token>' | docker login --username '<username>' --password-stdin docker.io
image_name: modelarts-cann:9.1.1-910b-ubuntu22.04
```

登录命令由本次运行临时提供，不读取仓库 Secrets；登录命令的标准输出和错误输出会被 workflow 抑制，不会进入 Actions 日志。由于手动输入仍会保留在 workflow run 的输入记录中，不要把它当作 Secret 长期使用。该 workflow 运行在新的 runner 上，因此镜像必须预先存在于该 runner 的 Docker daemon 中；GitHub-hosted runner 不会自动保留其它 workflow 构建的本地镜像。

默认发布到：

```text
ghcr.io/<github-owner>/<platform>-<runtime>:<tag>
ghcr.io/<github-owner>/<platform>-<runtime>:<tag>-r<YYMMDD.HHMMSS>
ghcr.io/<github-owner>/<platform>-<runtime>:latest
```

GitHub Actions 会优先使用手动输入的 `image_repositories`。如果该输入为空，会读取仓库变量 `IMAGE_REPOSITORIES`；如果变量也为空，才使用默认 GHCR owner 命名空间并自动追加分类仓库名。

`IMAGE_REPOSITORIES` 只能包含镜像仓库地址，不要写入用户名、密码、token 或 URL scheme。登录凭据必须放在 Secrets 中。

如果要发布到 DockerHub、Quay 或 Huawei Cloud SWR，需要在仓库 Secrets 中配置：

| 目标             | Secrets                                                                         |
| ---------------- | ------------------------------------------------------------------------------- |
| DockerHub        | `DOCKER_USERNAME`, `DOCKER_TOKEN`                                               |
| Quay.io          | `QUAY_USERNAME`, `QUAY_TOKEN`                                                   |
| Huawei Cloud SWR | `SWR_USERNAME`, `SWR_PASSWORD`；也兼容 `SWR_TOKEN` 或 `HW_USERNAME`, `HW_TOKEN` |

## 新增镜像版本

1. 新增目录 `images/<platform>/<runtime>/<tag>/Dockerfile`。
2. 如需配置衍生 tag、别名 tag、构建架构或 runner，在 `image_publish_version.json` 中新增一条 `versions` 记录。
3. 如果多个芯片只需要替换基础镜像，在模板记录中配置 `chip` 和 `derived_chips`。
4. 执行 `python3 scripts/image_metadata.py validate`。
5. 提交 PR，等待 `Build Images` 验证。
6. 合并后手动运行 `Build and Publish Image` 或 `Batch Build and Publish Images`。

更多发布细节见 [docs/release_process_zh.md](docs/release_process_zh.md)。
