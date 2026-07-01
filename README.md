# Runtime Container Images

本仓库维护面向 ModelArts 的多运行环境镜像，当前包含 CANN 和 CUDA 样例，并集成 GitHub Actions 构建、发布和批量发布流程。

## 目录结构

```text
images/<platform>/<runtime>/<tag>/Dockerfile # 镜像构建上下文
images/<platform>/<runtime>/scripts/         # 构建前复制到同类镜像上下文的运行时脚本
image_publish_version.json                   # 可选元数据：衍生芯片、别名 tag、平台和 runner
scripts/image_metadata.py                    # CI 和本地脚本共用的元数据解析工具
scripts/prepare_image_context.sh             # 构建前同步同类 scripts 到目标上下文
scripts/build_image.sh                       # 本地构建脚本
scripts/publish_image.sh                     # 本地 buildx 发布脚本
.github/workflows/build_images.yml
.github/workflows/build_and_push_image.yml
.github/workflows/batch_build_and_push_images.yml
```

目录前两级用于发布分类：`images/modelarts/cann/...` 发布到 `modelarts-cann`，`images/modelarts/cuda/...` 发布到 `modelarts-cuda`。

## 当前镜像

| 分类             | 标签                      | 基础镜像                                      | 默认用户  |
| ---------------- | ------------------------- | --------------------------------------------- | --------- |
| `modelarts-cann` | `9.0.0-910b-ubuntu22.04`  | `ascendai/cann:9.0.0-910b-ubuntu22.04-py3.11` | `ma-user` |
| `modelarts-cann` | `9.0.0-310p-ubuntu22.04`  | `ascendai/cann:9.0.0-310p-ubuntu22.04-py3.11` | `ma-user` |
| `modelarts-cann` | `9.0.0-910-ubuntu22.04`   | `ascendai/cann:9.0.0-910-ubuntu22.04-py3.11`  | `ma-user` |
| `modelarts-cann` | `9.0.0-950-ubuntu22.04`   | `ascendai/cann:9.0.0-950-ubuntu22.04-py3.11`  | `ma-user` |
| `modelarts-cann` | `9.0.0-a3-ubuntu22.04`    | `ascendai/cann:9.0.0-a3-ubuntu22.04-py3.11`   | `ma-user` |
| `modelarts-cuda` | `12.6.1-v100-ubuntu24.04` | `nvidia/cuda:12.6.1-cudnn-devel-ubuntu24.04`  | `ma-user` |

CANN 的 `9.0.0-910b-ubuntu22.04` 是模板目录，其它芯片版本由 `derived_chips` 自动展开，构建时仅替换 Dockerfile 顶层 `BASE_IMAGE`。CUDA 样例没有配置 `derived_chips`，会按实际目录直接构建。

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
  scripts/build_image.sh 12.6.1-v100-ubuntu24.04
```

发布镜像：

```bash
docker login ghcr.io
IMAGE_REPOSITORIES=ghcr.io/<owner> \
  scripts/publish_image.sh 9.0.0-910b-ubuntu22.04
```

`IMAGE_REPOSITORIES` 支持逗号或空白分隔的多个仓库。可以填写完整仓库，也可以只填写命名空间，脚本会按目录分类补齐末级仓库名：

```bash
IMAGE_REPOSITORIES="ghcr.io/<owner>,docker.io/<namespace>,swr.cn-southwest-2.myhuaweicloud.com/<organization>"
```

## GitHub Actions

- `Build Images`：PR 或 push 修改 `images/**` 时自动构建实际存在的 `images/<platform>/<runtime>/<tag>` 目录，不展开 `derived_chips`，不推送镜像。
- `Build and Publish Image`：手动或被其它 workflow 调用，支持只构建或构建并发布指定 tag。
- `Batch Build and Publish Images`：按 `image_version` 批量调用发布 workflow，会展开 CANN 的 `derived_chips`。

默认发布到：

```text
ghcr.io/<github-owner>/<platform>-<runtime>:<tag>
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
