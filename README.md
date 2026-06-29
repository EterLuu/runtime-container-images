# ModelArts CANN Container Image

本仓库提供基于 CANN 镜像的 ModelArts 适配镜像，并参考 `cann-container-image` 集成了 GitHub Actions 构建、发布和批量发布流程。

## 目录结构

```text
modelarts/<template-tag>/Dockerfile # 镜像模板构建上下文
modelarts_publish_version.json      # 镜像版本、衍生芯片、标签、平台和 runner 元数据
scripts/modelarts_metadata.py       # CI 和本地脚本共用的元数据解析工具
scripts/build_modelarts.sh          # 本地构建脚本
scripts/publish_modelarts.sh        # 本地 buildx 发布脚本
.github/workflows/build_modelarts.yml
.github/workflows/build_and_push_modelarts.yml
.github/workflows/batch_build_and_push_modelarts.yml
```

## 当前镜像

| 标签                     | 基础镜像                                      | 默认用户  | 默认 Conda 环境 |
| ------------------------ | --------------------------------------------- | --------- | --------------- |
| `9.0.0-910b-ubuntu22.04` | `ascendai/cann:9.0.0-910b-ubuntu22.04-py3.11` | `ma-user` | `torch_2.9`     |
| `9.0.0-310p-ubuntu22.04` | `ascendai/cann:9.0.0-310p-ubuntu22.04-py3.11` | `ma-user` | `torch_2.9`     |
| `9.0.0-910-ubuntu22.04`  | `ascendai/cann:9.0.0-910-ubuntu22.04-py3.11`  | `ma-user` | `torch_2.9`     |
| `9.0.0-950-ubuntu22.04`  | `ascendai/cann:9.0.0-950-ubuntu22.04-py3.11`  | `ma-user` | `torch_2.9`     |
| `9.0.0-a3-ubuntu22.04`   | `ascendai/cann:9.0.0-a3-ubuntu22.04-py3.11`   | `ma-user` | `torch_2.9`     |

`9.0.0-910b-ubuntu22.04` 是模板目录；其它芯片版本由 `derived_chips` 自动展开，构建时仅替换 Dockerfile 顶层 `BASE_IMAGE`。
镜像内置 ModelArts 常用用户和目录约定，并创建多个 Ascend NPU 适配的 PyTorch/torch-npu Conda 环境。

## 本地构建

先校验元数据和 Dockerfile 路径：

```bash
python3 scripts/modelarts_metadata.py validate
```

构建单个 tag：

```bash
IMAGE_REPOSITORY=modelarts-cann \
  scripts/build_modelarts.sh 9.0.0-310p-ubuntu22.04
```

发布多架构镜像：

```bash
docker login ghcr.io
IMAGE_REPOSITORIES=ghcr.io/<owner>/modelarts-cann \
  scripts/publish_modelarts.sh 9.0.0-910b-ubuntu22.04
```

`IMAGE_REPOSITORIES` 支持逗号或空白分隔的多个仓库，例如：

```bash
IMAGE_REPOSITORIES="ghcr.io/<owner>/modelarts-cann,docker.io/<namespace>/modelarts-cann"
```

## GitHub Actions

- `Build ModelArts Image`：PR 或 push 修改 `modelarts/**`、元数据、脚本或 workflow 时自动构建，不推送镜像。
- `Build and Publish ModelArts Image`：手动或被其他 workflow 调用，支持只构建或构建并发布指定 tag。
- `Batch Build and Publish ModelArts Image`：按 `modelarts_version` 批量调用发布 workflow。

默认发布到：

```text
ghcr.io/<github-owner>/modelarts-cann:<tag>
```

如果 `image_repositories` 为空，workflow 使用 GHCR 和 `GITHUB_TOKEN`。如果要发布到 DockerHub 或 Quay，需要在仓库 Secrets 中配置：

| 目标      | Secrets                           |
| --------- | --------------------------------- |
| DockerHub | `DOCKER_USERNAME`, `DOCKER_TOKEN` |
| Quay.io   | `QUAY_USERNAME`, `QUAY_TOKEN`     |

## 新增镜像版本

1. 新增目录 `modelarts/<tag>/Dockerfile`。
2. 在 `modelarts_publish_version.json` 中新增一条 `versions` 记录。
   如果多个芯片只需要替换基础镜像，在模板记录中配置 `chip` 和 `derived_chips`，无需新增多个 Dockerfile。
3. 执行 `python3 scripts/modelarts_metadata.py validate`。
4. 提交 PR，等待 `Build ModelArts Image` 验证。
5. 合并后手动运行 `Build and Publish ModelArts Image` 或 `Batch Build and Publish ModelArts Image`。

更多发布细节见 [docs/release_process_zh.md](docs/release_process_zh.md)。
